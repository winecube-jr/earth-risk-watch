"""Bounded HTTP access shared by open-data extractors."""

from collections.abc import Iterator
from contextlib import contextmanager

import httpx

USER_AGENT = "earth-risk-watch/0.1 (+https://github.com/earth-risk-watch)"


class DownloadTooLargeError(RuntimeError):
    """Raised before an extraction exceeds its configured memory budget."""


@contextmanager
def open_data_client(timeout_seconds: float = 30.0) -> Iterator[httpx.Client]:
    """Yield a redirect-aware client with an identifiable user agent."""
    with httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(timeout_seconds),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/csv, application/json, application/geo+json",
        },
    ) as client:
        yield client


def get_bytes(
    client: httpx.Client,
    url: str,
    *,
    max_bytes: int = 25_000_000,
    attempts: int = 3,
) -> bytes:
    """Download bounded bytes, retrying transient transport failures."""
    if attempts < 1:
        raise ValueError("attempts must be at least one")
    for attempt in range(attempts):
        try:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                declared = response.headers.get("content-length")
                if declared is not None and int(declared) > max_bytes:
                    raise DownloadTooLargeError(f"Declared download size exceeds {max_bytes} bytes")

                chunks: list[bytes] = []
                received = 0
                for chunk in response.iter_bytes():
                    received += len(chunk)
                    if received > max_bytes:
                        raise DownloadTooLargeError(f"Download exceeded {max_bytes} bytes")
                    chunks.append(chunk)
                return b"".join(chunks)
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == attempts - 1:
                raise
    raise RuntimeError("Download retry loop ended unexpectedly")
