import pytest

from aioreq.protocol.http import Response
from aioreq.parser.response_parser import ResponseParser

(
    (
        "HTTP/1.1 200 OK\r\n"
        "test: :test:test:ttest\r\n"
        "spacetest:          test\r\n"
        "messagetest:    hello 123\r\n"
        "\r\n"
    ),

    Response(
            scheme_and_version="HTTP/1.1",
            status=200,
            status_message="OK",
            headers={
                'test' : ':test:test:ttest',
                'spacetest' : 'test',
                'messagetest' : 'hello 123'
                },
            body='',
        )

    )

class TestResponseParser:
    """
    Check if aioreq.parser.request_parser works fine,
    do some parsing and compare with the expected results,
    checking some exceptions
    """

    @pytest.mark.parametrize(
            argnames=("response_raw", "expected_result"),
            argvalues=[
                (
                    (
                        "HTTP/1.1 200 OK\r\n"
                        "test: :test:test:ttest\r\n"
                        "spacetest:          test\r\n"
                        "messagetest:    hello 123\r\n"
                        "\r\n"
                    ),

                    Response(
                            scheme_and_version="HTTP/1.1",
                            status=200,
                            status_message="OK",
                            headers={
                                'test' : ':test:test:ttest',
                                'spacetest' : 'test',
                                'messagetest' : 'hello 123'
                                },
                            body='',
                        )

                ),
            ],
        )

    def test_parse(self,
                   response_raw: str,
                   expected_result: Response):
        
        result = ResponseParser.parse(response_raw)
        assert result == expected_result
    
    @pytest.mark.parametrize(
            argnames=('response_raw', 'expected_result'),
            argvalues=[
                (
                    (
                        'HTTP/1.1 200 OK\r\n'
                        "Host:   testhost\r\n"
                        "Content-leng"

                    ),
                    None
                ),
                (
                    (
                        'HTTP/1.1 200 OK\r\n'
                        "Host:   testhost\r\n"
                        "Content-length:   43\r\n"

                    ),
                    43
                ),
                (
                    (
                        'HTTP/1.1 200 OK\r\n'
                        "Host:   testhost\r\n"
                        "Content-length:   43\r"

                    ),
                    None
                ),
                (
                    (
                        'HTTP/1.1 200 OK\r\n'
                        "Host:   testhost\r\n"
                        "cOnteNt-LENGTH:      44\r\n"

                    ),
                    44
                ),
                (
                    (
                        'HTTP/1.1 200 OK\r\n'
                        "Host:   testhost\r\n"
                        "cOnteNt-LENGTH:44\r\n"

                    ),
                    44
                )


            ]
        )
    def test_content_length_found(self,
                                  response_raw: str,
                                  expected_result: int | None):
        result = ResponseParser.search_content_length(response_raw)
        assert result == expected_result
        
