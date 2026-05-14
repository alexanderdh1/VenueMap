import random
import time

import httpx

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_RETRYABLE_ERRORS = (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)


def get(client: httpx.Client, url: str, *, attempts: int = 4, **kwargs) -> httpx.Response:
    """GET with exponential backoff on transient network errors and retryable HTTP status codes.

    Waits between attempts: 1s, 2s, 4s (plus up to 1s random jitter each time).
    Retries on: connection errors, timeouts, HTTP 429/500/502/503/504.
    Raises the last exception if all attempts are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(attempts):
        if attempt > 0:
            wait = (2 ** (attempt - 1)) + random.uniform(0, 1)
            time.sleep(wait)
        try:
            resp = client.get(url, **kwargs)
            if resp.status_code not in _RETRYABLE_STATUSES:
                resp.raise_for_status()
                return resp
            last_exc = httpx.HTTPStatusError(
                f"Retryable status {resp.status_code}",
                request=resp.request,
                response=resp,
            )
        except _RETRYABLE_ERRORS as exc:
            last_exc = exc
    assert last_exc is not None
    raise last_exc
