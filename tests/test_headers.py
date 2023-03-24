import aioreq
from aioreq.http import Headers
from aioreq.settings import DEFAULT_HEADERS


def test_HeaderDict_base():
    headers = Headers(initial_headers={"content-LEngth": "200"})
    assert headers.get("content-lEngth") == "200"
    assert len(headers) == 1
    assert "content-length" in headers._headers


def test_header_override():
    headers = Headers()

    headers["Transfer-Encoding"] = "chunked"
    headers["Transfer-eNCoding"] = "gzip"

    assert headers["Transfer-Encoding"] == "gzip"
    assert "Transfer-Encoding" in headers
    assert "transFER-encoding" in headers


def test_header_correct_initialization():
    headers = Headers()
    new_headers = Headers(headers)
    assert headers is new_headers


def test_header_or():
    headers = Headers({"1": "2"})
    headers1 = Headers({"1": "3", "2": "4"})
    assert (headers | headers1)._headers == {"1": "3", "2": "4"}


def test_default_headers():
    cl = aioreq.Client()
    assert cl.headers._headers == DEFAULT_HEADERS
