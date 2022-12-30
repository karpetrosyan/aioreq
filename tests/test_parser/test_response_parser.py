import pytest

from aioreq.protocol.http import Response
from aioreq.parser.response_parser import ResponseParser


class TestResponseParser:
    """
    Check if aioreq.parser.request_parser works fine,
    do some parsing and compare with the expected results,
    checking some exceptions
    """

    @pytest.mark.parametrize(
        argnames=("response_raw", "wbl", "expected_result"),
        argvalues=[
            (
                    (
                            "HTTP/1.1 200 OK\r\n"
                            "test: :test:test:ttest\r\n"
                            "spacetest:          test\r\n"
                            "messagetest:    hello 123\r\n"
                            "\r\n"
                    ).encode(),
                    96,
                    Response(
                        status=200,
                        status_message="OK",
                        headers={
                            'test': ':test:test:ttest',
                            'spacetest': 'test',
                            'messagetest': 'hello 123'
                        },
                        content=b'',
                    )

            ),
        ],
    )
    def test_parse(self,
                   response_raw: bytes,
                   wbl,
                   expected_result: Response):
        result = ResponseParser.body_len_parse(response_raw, wbl)
        is_same = result == expected_result
        assert is_same
    @pytest.mark.parametrize(
        argnames=('response_raw', 'expected_result'),
        argvalues=[
            (
                    (
                            'HTTP/1.1 200 OK\r\n'
                            "Host:   testhost\r\n"
                            "Content-leng"

                    ).encode(),
                    None
            ),
            (
                    (
                            'HTTP/1.1 200 OK\r\n'
                            "Host:   testhost\r\n"
                            "Content-length:   43\r\n"

                    ).encode(),
                    43
            ),
            (
                    (
                            'HTTP/1.1 200 OK\r\n'
                            "Host:   testhost\r\n"
                            "Content-length:   43\r"

                    ).encode(),
                    None
            ),
            (
                    (
                            'HTTP/1.1 200 OK\r\n'
                            "Host:   testhost\r\n"
                            "cOnteNt-LENGTH:      44\r\n"

                    ).encode(),
                    44
            ),
            (
                    (
                            'HTTP/1.1 200 OK\r\n'
                            "Host:   testhost\r\n"
                            "cOnteNt-LENGTH:44\r\n"

                    ).encode(),
                    44
            )

        ]
    )
    def test_content_length_found(self,
                                  response_raw: bytes,
                                  expected_result: int | None):
        result = ResponseParser.search_content_length(response_raw)
        assert result == expected_result
