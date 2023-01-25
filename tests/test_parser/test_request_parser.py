import pytest

from aioreq.parser.request_parser import RequestParser
from aioreq.protocol.http import Request
from aioreq.protocol.http import JsonRequest


class TestRequestParser:
    """
    Check if aioreq.parser.request_parser works fine,
    do some parsing and compare with the expected results,
    checking some exceptions
    """

    @pytest.mark.parametrize(
        argnames=("request_obj", "expected_result"),
        argvalues=[
            (
                Request(
                    url="http://youtube.com",
                    method="GET",
                    headers={},
                ),
                "GET / HTTP/1.1\r\n" "host:  youtube.com\r\n" "\r\n",
            ),
            (
                Request(
                    url="http://chxko.am/chxkopath",
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
                    url="http://chxko.am/chxkopath",
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
                    url="http://chxko.am/chxkopath",
                    method="LINK",
                    headers={"testheader": "testvalue", "testchxko": "chxko"},
                    content="{'this is a test body data': 20}",
                ),
                (
                    "LINK /chxkopath HTTP/1.1\r\n"
                    "host:  chxko.am\r\n"
                    "testheader:  testvalue\r\n"
                    "testchxko:  chxko\r\n"
                    "content-type:  application/json\r\n"
                    "content-length:  32\r\n"
                    "\r\n"
                    "{'this is a test body data': 20}"
                ),
            ),
        ],
    )
    def test_parse(self, request_obj: Request, expected_result: str):
        """
        Check if request parsing works correctly

        :param request_obj: The Request object representing http request
        :param expected_result: String which is expected result for parsed request_obj
        :returns: None
        """

        parsed_data = type(request_obj).parser.parse(request_obj)
        assert parsed_data == expected_result
