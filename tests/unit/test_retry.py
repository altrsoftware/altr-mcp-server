"""Tests for HTTP retry logic in utils/api.py."""
import asyncio
import base64
import math

import httpx
import pytest
from pytest_httpx import HTTPXMock

from altr_mcp.utils import api
from altr_mcp.utils.api import _async_sleep, _clamp_retry_after, request


@pytest.fixture
def retry_env(monkeypatch):
    """Settings with retry enabled, 3 attempts, fast for tests."""
    monkeypatch.setenv("ORG_ID", "test-org")
    monkeypatch.setenv("MAPI_KEY", "test-key")
    monkeypatch.setenv("MAPI_SECRET", "test-secret")
    monkeypatch.setenv("MAX_RETRIES", "3")
    monkeypatch.setenv("DISABLE_RETRY", "false")


@pytest.fixture
def no_retry_env(monkeypatch):
    """Settings with retry disabled."""
    monkeypatch.setenv("ORG_ID", "test-org")
    monkeypatch.setenv("MAPI_KEY", "test-key")
    monkeypatch.setenv("MAPI_SECRET", "test-secret")
    monkeypatch.setenv("DISABLE_RETRY", "true")


@pytest.fixture
def sleep_calls(monkeypatch):
    """Record backoff durations and skip the wait. Returns the list.

    Patches api's own async seam, not tenacity.nap.sleep. The latter is
    synchronous, so patching it let a blocking implementation pass these
    tests -- see test_async_sleep_suspends and
    test_backoff_lets_other_tasks_run.
    """
    calls: list[float] = []

    async def _record(seconds):
        calls.append(seconds)

    monkeypatch.setattr(api, "_async_sleep", _record)
    return calls


async def test_successful_request(httpx_mock: HTTPXMock, retry_env):
    """200 response returns normal dict without retry interference."""
    httpx_mock.add_response(json={"success": True, "data": "ok"})
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True


async def test_retry_on_429(httpx_mock: HTTPXMock, retry_env, sleep_calls):
    """429 status code triggers retry; succeeds on second attempt."""
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(json={"success": True, "data": "ok"})
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True
    assert len(sleep_calls) == 1


async def test_retry_on_503(httpx_mock: HTTPXMock, retry_env, sleep_calls):
    """503 status code triggers retry."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(json={"success": True, "data": "ok"})
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True


async def test_no_retry_on_404(httpx_mock: HTTPXMock, retry_env):
    """404 status code fails immediately without retry."""
    httpx_mock.add_response(status_code=404)
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is False
    assert result["status_code"] == 404
    # Only 1 request made (no retry)
    assert len(httpx_mock.get_requests()) == 1


async def test_retry_exhausted_returns_error_dict(
        httpx_mock: HTTPXMock, retry_env, monkeypatch, sleep_calls):
    """After max_retries exhausted, returns {success: False} dict."""
    monkeypatch.setenv("MAX_RETRIES", "2")
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(status_code=429)
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is False
    assert result["status_code"] == 429
    assert "Retry exhausted" in result["message"]


async def test_retry_honors_retry_after_header(
        httpx_mock: HTTPXMock, retry_env, sleep_calls):
    """Retry-After header value is used as wait duration."""
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "5"})
    httpx_mock.add_response(json={"success": True, "data": "ok"})
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True
    # The sleep value should be 5.0 (from Retry-After header)
    assert 5.0 in sleep_calls


async def test_disable_retry_skips_retry(httpx_mock: HTTPXMock, no_retry_env):
    """DISABLE_RETRY=true returns error on first retryable status."""
    httpx_mock.add_response(status_code=429)
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is False
    assert result["status_code"] == 429
    assert "retry disabled" in result["message"]
    assert len(httpx_mock.get_requests()) == 1


async def test_async_sleep_suspends():
    """_async_sleep must yield control, not run straight through.

    _async_sleep used to delegate to tenacity.nap.sleep -- time.sleep --
    so a single retrying call froze the whole server for the length of its
    backoff. Every retry test above patches the sleep away, so this file
    would otherwise not notice at all.

    Driving the coroutine by hand rather than timing it: one send() into a
    correct implementation suspends at the inner await, while a blocking
    one completes its time.sleep and raises StopIteration. No timing, so
    nothing here can flake under load.

    Async despite never awaiting the coroutine it builds: asyncio.sleep
    calls get_running_loop() as soon as its body runs, so send() needs a
    live loop even though this test never lets the sleep finish.
    """
    coro = _async_sleep(0.05)
    try:
        coro.send(None)
    except StopIteration:
        pytest.fail(
            "_async_sleep ran to completion without suspending, so it is "
            "blocking the event loop rather than yielding"
        )
    finally:
        coro.close()


async def test_backoff_lets_other_tasks_run():
    """The same guarantee as above, observed as concurrency.

    Kept alongside the send() test because this is the property that
    actually matters -- other in-flight tool calls make progress -- and it
    would survive a rewrite of _async_sleep that suspends on something
    other than asyncio.sleep.

    A blocking implementation scores exactly 1: the counter's already-armed
    1ms timer fires once after stop.set(). Hence > 1, not > 0. Measured
    ~39 ticks idle and never below 21 under 3x CPU oversubscription, so the
    margin to 1 is wide.
    """
    ticks = 0
    stop = asyncio.Event()

    async def counter():
        nonlocal ticks
        while not stop.is_set():
            await asyncio.sleep(0.001)
            ticks += 1

    task = asyncio.create_task(counter())
    await asyncio.sleep(0)  # let the counter reach its first await
    await _async_sleep(0.05)
    stop.set()
    await task

    assert ticks > 1, (
        "the event loop made no progress during the backoff, so "
        "_async_sleep is blocking rather than yielding"
    )


@pytest.mark.parametrize("value,expected", [
    ("5", 5.0),
    ("0", 0.0),
    ("2.5", 2.5),
    ("  5  ", 5.0),
    ("120", 60.0),                                # clamped to the limit
    ("86400", 60.0),                              # clamped to the limit
    ("-1", None),                                 # nonsense; back off instead
    ("Wed, 21 Oct 2015 07:28:00 GMT", None),      # HTTP-date form
    ("soon", None),
    ("", None),
    ("   ", None),
    (None, None),
    # float() accepts all of these. nan is the dangerous one: it survives a
    # `< 0` test, and min(nan, limit) returns nan because every comparison
    # against NaN is False -- so without an isfinite() guard the clamp
    # returns nan and asyncio.sleep(nan) never wakes.
    ("nan", None),
    ("NaN", None),
    ("-nan", None),
    ("inf", None),
    ("Infinity", None),
    ("1e400", None),                              # overflows to inf
])
def test_clamp_retry_after(value, expected):
    """Retry-After is parsed as delta-seconds and bounded by the limit."""
    assert _clamp_retry_after(value, 60.0) == expected


async def test_nan_retry_after_cannot_wedge_the_call(
        httpx_mock: HTTPXMock, retry_env, sleep_calls):
    """A NaN Retry-After must not produce an unbounded wait.

    This is the clamp's own failure mode, not a hypothetical: `nan` parses,
    passes the negative check, and survives min(), and asyncio.sleep(nan)
    never fires -- `when = loop.time() + nan` is NaN and the timer heap
    comparison stays False. The call hung forever with no error reaching the
    MCP client, in the code path added to stop a server parking a call.
    """
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "nan"})
    httpx_mock.add_response(json={"success": True, "data": "ok"})
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True
    assert sleep_calls, "no backoff was taken"
    assert all(math.isfinite(s) for s in sleep_calls), (
        f"a non-finite sleep reached the event loop: {sleep_calls}"
    )


async def test_local_backoff_is_bounded_by_max_retry_after(
        httpx_mock: HTTPXMock, retry_env, monkeypatch, sleep_calls):
    """The locally computed backoff obeys the same ceiling as Retry-After.

    wait_exponential_jitter's own max is ~4.6e18s, so without an explicit
    bound a raised MAX_RETRIES reintroduces an effectively unbounded wait
    on the path the client controls: at MAX_RETRIES=10 the last wait
    actually taken is attempt 9's, ~256s.
    """
    monkeypatch.setenv("MAX_RETRIES", "8")
    monkeypatch.setenv("MAX_RETRY_AFTER", "3")
    for _ in range(7):
        httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(json={"success": True, "data": "ok"})

    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True
    assert len(sleep_calls) == 7
    assert max(sleep_calls) <= 3.0, (
        f"backoff exceeded MAX_RETRY_AFTER: {sleep_calls}"
    )


async def test_shared_client_does_not_carry_cookies(
        httpx_mock: HTTPXMock, retry_env):
    """A Set-Cookie from one call must not replay on the next.

    Per-request clients could never carry a cookie. Sharing one would
    otherwise share a jar for the life of the process, so ALB stickiness or
    a WAF challenge cookie would pin every later call to that host.
    """
    httpx_mock.add_response(
        headers={"Set-Cookie": "AWSALB=sticky; Path=/"}, json={"ok": True})
    httpx_mock.add_response(json={"ok": True})

    await request("GET", "https://api.example.com/one", None, {})
    await request("GET", "https://api.example.com/two", None, {})

    second = httpx_mock.get_requests()[1]
    assert "cookie" not in {k.lower() for k in second.headers}


def test_concurrent_loops_do_not_thrash_the_client(retry_env):
    """One client per loop, even when loops live on separate threads.

    get_client() reads and writes two globals; a thread switch between the
    assignments both handed out a client bound to another live loop (which
    raises inside httpx) and rebuilt the client on every alternation,
    defeating the reuse the cache exists for -- 17 clients for 4 loops.
    """
    import threading

    # Holds the objects, not their ids. id() is only a stable identity while
    # the object is alive, and nothing here forces the four threads to
    # overlap -- if one finishes before the next starts, its loop and client
    # become collectable and the next thread's can land on the same
    # addresses. Measured: recording ids and serializing the threads with a
    # gc.collect() between them reported "saw 2 loops" in 4 of 20 runs, on
    # correct code. Keeping the objects referenced in `seen` was 20 of 20.
    seen: list[tuple[asyncio.AbstractEventLoop, httpx.AsyncClient]] = []
    lock = threading.Lock()

    async def work():
        pairs = []
        for _ in range(50):
            client = api.get_client()
            pairs.append((asyncio.get_running_loop(), client))
            await asyncio.sleep(0)
        with lock:
            seen.extend(pairs)

    threads = [
        threading.Thread(target=lambda: asyncio.run(work()))
        for _ in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Safe to key on id() now: `seen` holds every object, so none can be
    # collected and have its address reused.
    by_loop: dict[int, set[int]] = {}
    for loop, client in seen:
        by_loop.setdefault(id(loop), set()).add(id(client))

    assert len(by_loop) == 4, f"expected 4 loops, saw {len(by_loop)}"
    for loop_id, clients in by_loop.items():
        assert len(clients) == 1, (
            f"loop {loop_id} saw {len(clients)} clients; the cache is "
            "thrashing between threads"
        )
    # No client may be shared between two loops -- httpx binds to the first.
    all_clients = [c for clients in by_loop.values() for c in clients]
    assert len(set(all_clients)) == 4, (
        "a client was handed to more than one event loop"
    )


async def test_retry_after_is_clamped_to_max(
        httpx_mock: HTTPXMock, retry_env, monkeypatch, sleep_calls):
    """A hostile Retry-After cannot park the call for longer than the cap.

    Every attempt counts against max_retries, so without the clamp nothing
    would cut a 24-hour wait short.
    """
    monkeypatch.setenv("MAX_RETRY_AFTER", "2")
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "86400"})
    httpx_mock.add_response(json={"success": True, "data": "ok"})
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True
    assert sleep_calls == [2.0]


async def test_unparseable_retry_after_falls_back_to_backoff(
        httpx_mock: HTTPXMock, retry_env, sleep_calls):
    """An HTTP-date Retry-After leaves exponential backoff in charge."""
    httpx_mock.add_response(
        status_code=429,
        headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"})
    httpx_mock.add_response(json={"success": True, "data": "ok"})
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True
    # wait_exponential_jitter(initial=1, jitter=1) -> first wait in [1, 2)
    assert sleep_calls and sleep_calls[0] >= 1.0


async def test_request_builds_exactly_one_client(
        httpx_mock: HTTPXMock, retry_env, monkeypatch):
    """Two calls must construct one client, so the pool survives between.

    Counts constructions rather than comparing get_client() to itself. An
    earlier version of this test did the latter and passed even with
    request() building a client per call, because the only client it ever
    observed was the one the test itself had just cached.
    """
    built = 0
    real_init = httpx.AsyncClient.__init__

    def counting_init(self, *args, **kwargs):
        nonlocal built
        built += 1
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", counting_init)

    httpx_mock.add_response(json={"success": True})
    httpx_mock.add_response(json={"success": True})
    await request("GET", "https://api.example.com/one", None, {})
    await request("GET", "https://api.example.com/two", None, {})

    assert built == 1, f"expected one shared client, {built} were built"


async def test_forget_client_builds_a_fresh_one(retry_env):
    """forget_client drops the cache; the next call builds a new client."""
    first = api.get_client()
    api.forget_client()
    assert api.get_client() is not first


async def test_client_is_rebuilt_once_closed(retry_env):
    """A closed client is replaced rather than handed out again."""
    first = api.get_client()
    await first.aclose()
    assert api.get_client() is not first


def test_client_is_not_carried_into_another_event_loop(retry_env):
    """Each loop gets its own client.

    httpx binds anyio primitives to the loop that first drives a client, so
    one reused across loops raises instead of reconnecting. Sync test on
    purpose: it needs to own the loops.
    """
    async def grab():
        return api.get_client()

    first = asyncio.run(grab())
    second = asyncio.run(grab())
    assert second is not first


async def test_request_timeout_is_applied(
        httpx_mock: HTTPXMock, retry_env, monkeypatch):
    """REQUEST_TIMEOUT reaches the outgoing request."""
    monkeypatch.setenv("REQUEST_TIMEOUT", "7.5")
    httpx_mock.add_response(json={"success": True})
    await request("GET", "https://api.example.com/test", None, {})
    sent = httpx_mock.get_requests()[0]
    # Derived from httpx rather than hardcoded: the four-key shape is
    # Timeout.as_dict()'s, not a public contract, so a hardcoded dict would
    # break on an httpx upgrade that adds a phase. Still pins 7.5.
    assert sent.extensions["timeout"] == httpx.Timeout(7.5).as_dict()


async def test_auth_reaches_the_request(httpx_mock: HTTPXMock, retry_env):
    """Credentials must survive the move to a shared client.

    Auth moved from AsyncClient(auth=auth) to a per-request kwarg when the
    client became shared -- the highest-risk edit in that change, and
    nothing covered it. Deleting the kwarg entirely, which would mean
    blanket 401s against every ALTR service, passed the whole suite.
    """
    httpx_mock.add_response(json={"success": True})
    auth = httpx.BasicAuth(username="test-key", password="test-secret")
    await request("GET", "https://api.example.com/test", auth, {})
    expected = base64.b64encode(b"test-key:test-secret").decode()
    assert httpx_mock.get_requests()[0].headers["Authorization"] == (
        f"Basic {expected}"
    )


async def test_auth_is_reapplied_on_each_retry(
        httpx_mock: HTTPXMock, retry_env, sleep_calls):
    """A retried attempt carries credentials too, not just the first."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(json={"success": True})
    auth = httpx.BasicAuth(username="test-key", password="test-secret")
    result = await request("GET", "https://api.example.com/test", auth, {})
    assert result["success"] is True
    sent = httpx_mock.get_requests()
    assert len(sent) == 2
    assert all("Authorization" in r.headers for r in sent)


async def test_no_auth_sends_no_authorization_header(
        httpx_mock: HTTPXMock, retry_env):
    """auth=None must not pick up credentials from the shared client.

    The client is shared across every ALTR service, so an auth set on it
    would leak to callers that pass None.
    """
    httpx_mock.add_response(json={"success": True})
    await request("GET", "https://api.example.com/test", None, {})
    assert "Authorization" not in httpx_mock.get_requests()[0].headers
