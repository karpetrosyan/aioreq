import pytest
import aioreq
from aioreq.protocol.headers import SetCookie
from datetime import datetime

parser = SetCookie.parser


class TestCookieParser:

    @pytest.mark.parametrize(
        argnames=["text", "expected"],
        argvalues=[
            (
                    "__Secure-ID=1l23; Secure; Domain=example.com; HttpOnly",
                    {"key": "__Secure-ID",
                     "value": "1l23",
                     "attrs": {"Secure": None,
                               "Domain": "example.com",
                               "HttpOnly": None}
                     }
            ),
            (
                    "sessionId=38afes7a8",
                    {"key": "sessionId",
                     "value": "38afes7a8",
                     "attrs": {}}
            ),
            (
                    "id=a3fWa; Expires=Wed, 21 Oct 2015 07:28:00 GMT",
                    {"key": "id",
                     "value": "a3fWa",
                     "attrs": {"Expires": datetime.strptime("Wed, 21 Oct 2015 07:28:00 GMT", "%a, %d %b %Y %H:%M:%S %Z")}}
            ),
            (
                    "qwerty=219ffwef9w0f; Domain=somecompany.co.uk",
                    {"key": "qwerty",
                     "value": "219ffwef9w0f",
                     "attrs": {
                         "Domain": "somecompany.co.uk"
                     }}
            ),
            (
                    "__Host-example=34d8g; SameSite=None; Secure; Path=/; Partitioned",
                    {"key": "__Host-example",
                     "value": "34d8g",
                     "attrs": {
                         "SameSite": "None",
                         "Secure": None,
                         "Path": "/",
                         "Partitioned": None
                     }}
            )
        ]
    )
    def test_parsing(self, text, expected):
        set_cookie = SetCookie.parse(text)
        assert set_cookie.key == expected['key']
        assert set_cookie.value == expected['value']
        assert set_cookie.attrs == expected['attrs']
