import pytest

from aioreq.parser.request_parser import RequestParser
from aioreq.protocol.http import Request


class TestRequestParser:

    @pytest.mark.parametrize(
            argnames=("request_obj", "expected_result"),
            argvalues=[
                (
                    Request(
                        method="GET",
                        host="youtube.com",
                        path='/',
                        headers={},
                        ),
                    (
                        "GET / HTTP/1.1\r\n"
                        "Host:  youtube.com\r\n"
                        "\r\n"
                        )
                ),
                (
                    Request(
                        method="POST",
                        host="chxko.am",
                        path='/chxkopath',
                        headers={
                            'testheader' : "testvalue",
                            'testchxko'  : "chxko"
                            }
                        ),
                    (
                        "POST /chxkopath HTTP/1.1\r\n"
                        "Host:  chxko.am\r\n"
                        "testheader:  testvalue\r\n"
                        "testchxko:  chxko\r\n"
                        "\r\n"
                        )
                    
                ),
                (
                    Request(
                        method="HEAD",
                        host="chxko.am",
                        path='/chxkopath',
                        headers={
                            'testheader' : "testvalue",
                            'testchxko'  : "chxko"
                            },
                        body="this is a test body data",
                        ),
                    (
                        "HEAD /chxkopath HTTP/1.1\r\n"
                        "Host:  chxko.am\r\n"
                        "testheader:  testvalue\r\n"
                        "testchxko:  chxko\r\n"
                        "Content-Length:  24\r\n"
                        "\r\n"
                        "this is a test body data"
                        )
 
                    ),
                (
                    Request(
                        method="LINK",
                        host="chxko.am",
                        path='/chxkopath',
                        headers={
                            'testheader' : "testvalue",
                            'testchxko'  : "chxko"
                            },
                        json="{'this is a test body data': 20}",
                        ),
                    (
                        "LINK /chxkopath HTTP/1.1\r\n"
                        "Host:  chxko.am\r\n"
                        "testheader:  testvalue\r\n"
                        "testchxko:  chxko\r\n"
                        "Content-Length:  34\r\n"
                        "Content-Type:  application/json\r\n"
                        "\r\n"
                        '"{\'this is a test body data\': 20}"'
                        )
 
                    )
 

                ],
            )

    def test_parse(self,
                   request_obj: Request,
                   expected_result: str):

        parsed_data = RequestParser.parse(request_obj)
        assert parsed_data == expected_result

    def test_body_and_json_capability(self):

        with pytest.raises(Exception, match=r"Body and Json") as e:
            Request(
                method="HEAD",
                host="chxko.am",
                path='/chxkopath',
                headers={
                    'testheader' : "testvalue",
                    'testchxko'  : "chxko"
                    },
                body="this is a test body data",
                json="this is a json body data"
                )


