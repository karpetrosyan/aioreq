import pytest

from aioreq.http import JsonRequest, UrlEncodedRequest
from aioreq.http import Request
from aioreq.parsers import default_parser
from aioreq.urls import parse_url


class TestRequestParser:
    @pytest.mark.parametrize(
        argnames=("request_obj", "expected_result"),
        argvalues=[
            (
                Request(
                    url=parse_url("http://youtube.com"),
                    method="GET",
                    headers={},
                ),
                "GET / HTTP/1.1\r\n" "host:  youtube.com\r\n" "\r\n",
            ),
            (
                Request(
                    url=parse_url("http://youtube.com?a=1&b=2"),
                    method="GET",
                    headers={},
                ),
                "GET /?a=1&b=2 HTTP/1.1\r\n" "host:  youtube.com\r\n" "\r\n",
            ),
            (
                Request(
                    url=parse_url("http://youtube.com"),
                    method="GET",
                    params={"a": "1", "b": "2"},
                    headers={},
                ),
                "GET /?a=1&b=2 HTTP/1.1\r\n" "host:  youtube.com\r\n" "\r\n",
            ),
            (
                Request(
                    url=parse_url("http://chxko.am/chxkopath"),
                    method="POST",
                    headers={"testheader": "testvalue", "TEstchxko": "chxko"},
                ),
                (
                    "POST /chxkopath HTTP/1.1\r\n"
                    "host:  chxko.am\r\n"
                    "testheader:  testvalue\r\n"
                    "testchxko:  chxko\r\n"
                    "\r\n"
                ),
            ),
            (
                Request(
                    url=parse_url("http://chxko.am/chxkopath"),
                    method="HEAD",
                    headers={"testheader": "testvalue", "testchxko": "chxko"},
                    content="this is a test body data",
                ),
                (
                    "HEAD /chxkopath HTTP/1.1\r\n"
                    "host:  chxko.am\r\n"
                    "testheader:  testvalue\r\n"
                    "testchxko:  chxko\r\n"
                    "content-length:  24\r\n"
                    "\r\n"
                    "this is a test body data"
                ),
            ),
            (
                JsonRequest(
                    url=parse_url("http://chxko.am/chxkopath"),
                    method="LINK",
                    headers={"testheader": "testvalue", "testchxko": "chxko"},
                    content={"this is a test body data": 20},
                ),
                (
                    "LINK /chxkopath HTTP/1.1\r\n"
                    "host:  chxko.am\r\n"
                    "testheader:  testvalue\r\n"
                    "testchxko:  chxko\r\n"
                    "content-type:  application/json\r\n"
                    "content-length:  32\r\n"
                    "\r\n"
                    '{"this is a test body data": 20}'
                ),
            ),
            (
                    UrlEncodedRequest(
                        url=parse_url("http://chxko.am/chxkopath"),
                        method="LINK",
                        headers={"testheader": "testvalue", "testchxko": "chxko"},
                        content=(('a', 'b'), ('c', 'd')),
                    ),
                    (
                            "LINK /chxkopath HTTP/1.1\r\n"
                            "host:  chxko.am\r\n"
                            "testheader:  testvalue\r\n"
                            "testchxko:  chxko\r\n"
                            "content-type:  application/x-www-form-urlencoded\r\n"
                            "content-length:  7\r\n"
                            "\r\n"
                            'a=b&c=d'
                    ),
            ),
        ],
    )
    def test_parse(self, request_obj: Request, expected_result: str):
        parsed_data = default_parser(request_obj)
        assert parsed_data == expected_result

    def test_query_collision(self):
        with pytest.raises(ValueError, match=".*URL or as an argument*"):
            Request(url="https://example.com?a=1", params={"a": "2"})
