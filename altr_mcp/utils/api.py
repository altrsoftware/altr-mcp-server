import asyncio
import http.cookiejar
import math
import threading
import weakref

import structlog
import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from altr_mcp.settings import get_settings

logger = structlog.get_logger(__name__)


class _RetryableError(Exception):
    """Raised for HTTP status codes that should trigger retry."""
    def __init__(self, status_code: int, retry_after: str | None = None):
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(f"Retryable HTTP {status_code}")


_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


async def _async_sleep(seconds: float) -> None:
    """Wait `seconds` without blocking the event loop.

    tenacity's own nap.sleep is time.sleep. Handing that to AsyncRetrying
    stalls every other in-flight tool call for the length of the backoff,
    which makes the server's concurrency illusory the moment one call hits
    a 429.

    Tests patch this module attribute. The earlier seam was
    tenacity.nap.sleep, which is synchronous -- so a blocking stand-in
    satisfied it, and the tests passed while production blocked.
    """
    await asyncio.sleep(seconds)


# One client per event loop, so connections and TLS sessions are reused
# across calls. Building a client per request discards the pool every time:
# a fresh handshake on every call and on every retry.
#
# Keyed by loop because httpx binds anyio primitives to the loop that first
# drives a client; one carried into a different loop raises rather than
# reconnecting. A single slot would not do: with two live loops each lookup
# evicts the other's client, so every call rebuilds and the reuse this
# exists for is lost. Weak keys so a finished loop's entry disappears with
# it.
#
# In the server this is exactly one loop and one client, deliberately never
# closed -- keepalive_expiry reaps idle connections and the OS reclaims the
# rest at exit. Under pytest each test gets its own loop, and the autouse
# fixture in tests/conftest.py clears the map between tests.
_clients: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()
# Guards _clients. Within one loop the body below is already atomic -- it
# contains no await, so no other coroutine can interleave. The lock is for
# threads: FastMCP runs a *sync* tool body on anyio.to_thread, and a thread
# switch mid-update let one thread receive a client born in another live
# loop, which then raised "bound to a different event loop" from inside
# httpx. Every tool is async today, so that is latent rather than live.
_clients_lock = threading.Lock()


def get_client() -> httpx.AsyncClient:
    """Return the shared client for the running event loop.

    Auth and timeout are passed per request rather than set on the client,
    so one client serves every ALTR service and every credential.
    """
    loop = asyncio.get_running_loop()
    with _clients_lock:
        client = _clients.get(loop)
        if client is None or client.is_closed:
            # Only a default for a caller that forgets a per-request
            # timeout=, which wins in either direction, including downward.
            # It matters because httpx's own default is 5s, short for a
            # report download. Frozen at construction for the life of the
            # loop, and every caller today passes its own, so this is a
            # backstop rather than a live value.
            #
            # Constructed under the lock: it costs ~10ms, almost all of it
            # loading the CA bundle. Once per loop, and once per process in
            # the server, so it is not worth a double-checked lock that
            # would build and discard a client on every race.
            client = httpx.AsyncClient(
                timeout=get_settings().request_timeout)
            # A shared client would otherwise share one cookie jar for the
            # life of the loop: a Set-Cookie from any call -- ALB
            # stickiness, a WAF challenge -- would replay on every later
            # call to that host, where a per-request client could never
            # carry one. Rejecting all cookies keeps this refactor
            # behavior-neutral; nothing in the ALTR API needs them.
            client.cookies.jar.set_policy(
                http.cookiejar.DefaultCookiePolicy(allowed_domains=[]))
            _clients[loop] = client
        return client


def forget_client() -> None:
    """Drop every cached client so the next call builds a fresh one.

    For test isolation, and single-threaded on purpose: it clears every
    loop's entry rather than the caller's, because sync fixture teardown
    has no running loop to key on. Do not call it while another thread is
    driving a loop -- that thread's client would be finalized here, on this
    thread, closing sockets its selector still has registered.

    Deliberately does not await aclose(): under CPython refcounting the
    pool's sockets close as soon as the last reference drops.
    """
    with _clients_lock:
        _clients.clear()


def _clamp_retry_after(value, limit: float) -> float | None:
    """Parse a Retry-After delta-seconds value, bounded by `limit`.

    Returns None when the header is absent, negative, or not a number --
    which covers the HTTP-date form -- leaving the caller on exponential
    backoff.

    The bound matters because the value is server-controlled: honoring
    `Retry-After: 86400` verbatim would park the call for a day, and every
    attempt still counts against max_retries, so nothing else would end it.
    """
    try:
        seconds = float(value)
    except (ValueError, TypeError):
        return None
    # "nan" and "inf" both parse. NaN has to be rejected before the min():
    # every comparison against NaN is False, so min() keeps its first
    # argument and min(nan, limit) is nan -- and asyncio.sleep(nan) never
    # fires, because `when = loop.time() + nan` is NaN and the timer heap
    # comparison stays False. That would turn the clamp meant to bound the
    # wait into an unbounded one. Neither is a valid header value, so both
    # fall back to backoff rather than being clamped to the limit.
    if not math.isfinite(seconds) or seconds < 0:
        return None
    return min(seconds, limit)


def _failure_message(exc: Exception) -> str:
    """`Type: detail`, or bare `Type` when the exception carries no message.

    httpx's timeout exceptions stringify to "", which yielded a dangling
    "PoolTimeout: " with nothing after the colon. That one is newly
    reachable now that the connection pool is shared, so an unrelated call
    saturating it must at least name itself.
    """
    detail = str(exc)
    return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__


def _log_retry_attempt(retry_state):
    """Log each retry attempt; honor Retry-After header if present."""
    exc = retry_state.outcome.exception()
    retry_after = getattr(exc, "retry_after", None)
    logger.debug(
        "retrying_request",
        attempt=retry_state.attempt_number,
        status_code=getattr(exc, "status_code", None),
        retry_after=retry_after,
    )
    # Replace the upcoming backoff with Retry-After when the server sent a
    # usable value. upcoming_sleep is consumed by DoSleep; next_action.sleep
    # mirrors it.
    if retry_after is None:
        return
    seconds = _clamp_retry_after(retry_after, get_settings().max_retry_after)
    if seconds is None:
        return  # Unparseable or negative: fall back to exponential backoff
    retry_state.upcoming_sleep = seconds
    if retry_state.next_action is not None:
        retry_state.next_action.sleep = seconds


async def request(
        method: str, url: str, auth, params: dict,
        data=None, headers: dict | None = None) -> dict:
    """
    Generic HTTP helper with automatic retry on transient errors.
    Retries on 429 and 5xx status codes with exponential backoff + jitter.
    Honors Retry-After when present, bounded by MAX_RETRY_AFTER.
    """
    settings = get_settings()
    params = params or {}

    async def _do_request():
        request_kwargs = {
            "method": method,
            "url": url,
            "params": params,
            "auth": auth,
            "timeout": settings.request_timeout,
        }
        if data is not None:
            request_kwargs["json"] = data
        if headers is not None:
            request_kwargs["headers"] = headers

        response = await get_client().request(**request_kwargs)

        # Check for retryable status before raise_for_status
        if response.status_code in _RETRYABLE_STATUS_CODES:
            retry_after = response.headers.get("Retry-After")
            raise _RetryableError(response.status_code, retry_after)

        response.raise_for_status()

        # Handle empty responses
        if not response.content:
            return {
                "success": True,
                "status_code": response.status_code,
                "raw": None,
            }

        # Try JSON, fall back to text
        try:
            body = response.json()
        except ValueError:
            return {
                "success": True,
                "status_code": response.status_code,
                "raw": response.text,
            }

        # Return dict as-is, wrap other types
        return body if isinstance(body, dict) else {
            "success": True,
            "status_code": response.status_code,
            "data": body,
        }

    # No retry path
    if settings.disable_retry:
        try:
            return await _do_request()
        except _RetryableError as e:
            logger.error(
                "request_failed_no_retry",
                status_code=e.status_code, url=url)
            return {
                "success": False,
                "status_code": e.status_code,
                "message": f"HTTP {e.status_code} (retry disabled)",
            }
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response else None
            body = e.response.text if e.response else None
            return {
                "success": False,
                "status_code": status,
                "message": str(e),
                "body": body,
            }
        except Exception as e:
            logger.error(
                "request_failed", error=_failure_message(e), url=url)
            return {
                "success": False,
                "message": _failure_message(e),
            }

    # Retry path
    try:
        async for attempt in AsyncRetrying(
            sleep=_async_sleep,
            stop=stop_after_attempt(settings.max_retries),
            # max= bounds the locally computed wait by the same ceiling as a
            # server-sent one. Without it the default is ~4.6e18s, so a
            # raised MAX_RETRIES quietly reintroduces the unbounded wait
            # this clamp exists to prevent: at MAX_RETRIES=10 the last wait
            # taken is attempt 9's, ~256s. (stop_after_attempt(10) fires
            # after attempt 10, so attempt 10's own ~512s is never slept.)
            wait=wait_exponential_jitter(
                initial=1, jitter=1, max=settings.max_retry_after),
            retry=retry_if_exception_type(_RetryableError),
            before_sleep=_log_retry_attempt,
            reraise=True,
        ):
            with attempt:
                return await _do_request()
    except _RetryableError as e:
        logger.error(
            "request_exhausted_retries",
            status_code=e.status_code,
            url=url,
            max_retries=settings.max_retries,
        )
        return {
            "success": False,
            "status_code": e.status_code,
            "message": (
                f"Retry exhausted after {settings.max_retries}"
                f" attempts (HTTP {e.status_code})"
            ),
        }
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response else None
        body = e.response.text if e.response else None
        return {
            "success": False,
            "status_code": status,
            "message": str(e),
            "body": body,
        }
    except Exception as e:
        logger.error("request_failed", error=_failure_message(e), url=url)
        return {"success": False, "message": _failure_message(e)}
