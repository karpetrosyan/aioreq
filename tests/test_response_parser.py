import pytest

from aioreq.parsers import ResponseParser
from aioreq.http import Response


class TestResponseParser:
    """
    Check if aioreq.parser.request_parser works fine,
    do some parsing and compare with the expected results,
    checking some exceptions
    """

    @pytest.mark.parametrize(
        argnames=("status_line", "header_line", "content", "expected_result"),
        argvalues=[
            (
                ("HTTP/1.1 200 OK\r\n"),
                (
                    "test: :test:test:ttest\r\n"
                    "spacetest:          test\r\n"
                    "messagetest:    hello 123\r\n"
                    "\r\n"
                ),
                (b""),
                Response(
                    status=200,
                    status_message="OK",
                    headers={
                        "test": ":test:test:ttest",
                        "spacetest": "test",
                        "messagetest": "hello 123",
                    },
                    content=b"",
                ),
            ),
        ],
    )
    def test_parse(self, status_line, header_line, content, expected_result):
        result = ResponseParser.parse(status_line, header_line, content)
        assert result.status == expected_result.status
        assert result.status_message == expected_result.status_message
        assert result.headers == expected_result.headers
        assert result.content == expected_result.content

    @pytest.mark.parametrize(
        argnames=("response_raw", "expected_result"),
        argvalues=[
            (
                ("HTTP/1.1 200 OK\r\n" "Host:   testhost\r\n" "Content-leng").encode(),
                None,
            ),
            (
                (
                    "HTTP/1.1 200 OK\r\n"
                    "Host:   testhost\r\n"
                    "Content-length:   43\r\n"
                ).encode(),
                43,
            ),
            (
                (
                    "HTTP/1.1 200 OK\r\n"
                    "Host:   testhost\r\n"
                    "Content-length:   43\r"
                ).encode(),
                None,
            ),
            (
                (
                    "HTTP/1.1 200 OK\r\n"
                    "Host:   testhost\r\n"
                    "cOnteNt-LENGTH:      44\r\n"
                ).encode(),
                44,
            ),
            (
                (
                    "HTTP/1.1 200 OK\r\n" "Host:   testhost\r\n" "cOnteNt-LENGTH:44\r\n"
                ).encode(),
                44,
            ),
        ],
    )
    def test_content_length_found(self, response_raw, expected_result):
        result = ResponseParser.search_content_length(response_raw.decode())
        assert result == expected_result
