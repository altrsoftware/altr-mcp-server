import structlog
import httpx
import tenacity.nap
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
    """Async sleep wrapper that delegates to tenacity.nap.sleep.

    Using nap.sleep (rather than asyncio.sleep directly) allows tests to
    monkeypatch tenacity.nap.sleep to intercept and inspect sleep values.
    """
    tenacity.nap.sleep(seconds)


def _log_retry_attempt(retry_state):
    """Log each retry attempt; honor Retry-After header if present."""
    exc = retry_state.outcome.exception()
    logger.debug(
        "retrying_request",
        attempt=retry_state.attempt_number,
        status_code=getattr(exc, "status_code", None),
        retry_after=getattr(exc, "retry_after", None),
    )
    # Honor Retry-After header if present by overriding the upcoming sleep.
    # upcoming_sleep is consumed by DoSleep; next_action.sleep mirrors it.
    if hasattr(exc, "retry_after") and exc.retry_after:
        try:
            sleep_seconds = float(exc.retry_after)
            retry_state.upcoming_sleep = sleep_seconds
            if retry_state.next_action is not None:
                retry_state.next_action.sleep = sleep_seconds
        except (ValueError, TypeError):
            pass  # Fall back to exponential backoff


async def request(
        method: str, url: str, auth, params: dict,
        data=None) -> dict:
    """
    Generic HTTP helper with automatic retry on transient errors.
    Retries on 429 and 5xx status codes with exponential backoff + jitter.
    Honors Retry-After header when present.
    """
    settings = get_settings()
    params = params or {}

    async def _do_request():
        async with httpx.AsyncClient(auth=auth, timeout=30.0) as client:
            request_kwargs = {
                "method": method,
                "url": url,
                "params": params,
            }
            if data is not None:
                request_kwargs["json"] = data

            response = await client.request(**request_kwargs)

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
            return {"success": False, "status_code": status, "message": str(e)}
        except Exception as e:
            return {
                "success": False,
                "message": f"{type(e).__name__}: {str(e)}",
            }

    # Retry path
    try:
        async for attempt in AsyncRetrying(
            sleep=_async_sleep,
            stop=stop_after_attempt(settings.max_retries),
            wait=wait_exponential_jitter(initial=1, jitter=1),
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
        return {"success": False, "status_code": status, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"{type(e).__name__}: {str(e)}"}
