import httpx
import pytest
import respx

from earth_risk_watch.http_client import DownloadTooLargeError, get_bytes


@respx.mock
def test_get_bytes() -> None:
    route = respx.get("https://example.test/data").mock(
        return_value=httpx.Response(200, content=b'{"ok": true}')
    )
    with httpx.Client() as client:
        assert get_bytes(client, "https://example.test/data") == b'{"ok": true}'
    assert route.called


@respx.mock
def test_get_bytes_rejects_large_declared_response() -> None:
    respx.get("https://example.test/large").mock(
        return_value=httpx.Response(200, headers={"content-length": "100"}, content=b"x")
    )
    with httpx.Client() as client, pytest.raises(DownloadTooLargeError):
        get_bytes(client, "https://example.test/large", max_bytes=10)
