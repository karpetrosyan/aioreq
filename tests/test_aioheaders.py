import pytest

from aioreq.headers import Accept
from aioreq.headers import AuthenticationWWW
from aioreq.headers import ContentType
from aioreq.headers import MimeType
from aioreq.headers import SetCookie
from aioreq.urls import UriParser3986


class TestSetCookie:
    @pytest.mark.parametrize(
        "value, uri, expected",
        [
            (
                "key=value",
                UriParser3986().parse("https://example.com"),
                dict(
                    key="key",
                    value="value",
                    persistent_flag=False,
                    domain="example.com",
                    host_only_flag=True,
                    secure_only_flag=False,
                    http_only_flag=False,
                ),
            ),
            (
                (
                    "GPS=1; Domain=youtube.com; Expires=Tue, "
                    "07-Feb-2023 13:20:04 GMT; Path=/; Secure; HttpOnly"
                ),
                UriParser3986().parse("https://youtube.com"),
                dict(
                    key="GPS",
                    value="1",
                    persistent_flag=True,
                    domain="youtube.com",
                    host_only_flag=False,
                    secure_only_flag=True,
                    http_only_flag=True,
                ),
            ),
            (
                (
                    "ASD=1; Expires=Tue, "
                    "07-Feb-2023 13:20:04 GMT; Domain=youtube.com; "
                    "Secure; HttpOnly; Path=/"
                ),
                UriParser3986().parse("https://youtube.com"),
                dict(
                    key="ASD",
                    value="1",
                    persistent_flag=True,
                    domain="youtube.com",
                    host_only_flag=False,
                    secure_only_flag=True,
                    http_only_flag=True,
                ),
            ),
            (
                "test=test1; Domain=youtube.com; " "Secure; Path=/",
                UriParser3986().parse("https://youtube.com"),
                dict(
                    key="test",
                    value="test1",
                    persistent_flag=False,
                    domain="youtube.com",
                    host_only_flag=False,
                    secure_only_flag=True,
                    http_only_flag=False,
                ),
            ),
        ],
    )
    def test_cookie_parse(self, value, uri, expected):
        cookie = SetCookie().parse(value, uri)
        assert cookie.key == expected["key"]
        assert cookie.value == expected["value"]
        assert cookie.persistent_flag == expected["persistent_flag"]
        assert cookie.domain == expected["domain"]
        assert cookie.host_only_flag == expected["host_only_flag"]
        assert cookie.secure_only_flag == expected["secure_only_flag"]
        assert cookie.http_only_flag == expected["http_only_flag"]


class TestAuthenticateWWW:
    @pytest.mark.parametrize(
        argnames=("value", "expected"),
        argvalues=[
            (
                ['Basic realm="test"', 'Digest realm="asdf"'],
                "<AuthenticationWWW {'Basic': "
                "{'realm': '\"test\"'}, 'Digest': {'realm': "
                "'\"asdf\"'}}>",
            ),
            (
                ['Basic realm="test1", arg1="test2"'],
                "<AuthenticationWWW {'Basic': {'realm': '\"test1\"', 'arg1': "
                "'\"test2\"'}}>",
            ),
            (
                ['Basic realm="Fake Realm"'],
                "<AuthenticationWWW {'Basic': {'realm': '\"Fake Realm\"'}}>",
            ),
        ],
    )
    def test_parse(self, value, expected):
        assert repr(AuthenticationWWW.parse(value)) == expected


class TestAccept:
    @pytest.mark.parametrize(
        argnames=["value", "expected"],
        argvalues=[
            (
                Accept((MimeType.js, 1), (MimeType.avl, None)).value,
                " text/javascript; q=1, video/x-msvideo; q=1",
            ),
            (
                Accept((MimeType.js, 0.5), (MimeType.avl, None)).value,
                " text/javascript; q=0.5, video/x-msvideo; q=1",
            ),
            (
                Accept(
                    (MimeType.js, 0.5), (MimeType.avl, None), (MimeType.csv, 0.1)
                ).value,
                " text/javascript; q=0.5, video/x-msvideo; q=1, text/csv; q=0.1",
            ),
        ],
    )
    def test_parse(self, value, expected):
        assert value == expected


class TestContentType:
    def test_full_content_type(self):
        header_value = " application/html; charset='utf-8'"
        content_type = ContentType.parse(header_value)
        assert content_type.mime == MimeType.html
        assert content_type.charset == "utf-8"

    def test_case_insensitivity_content_type(self):
        header_value = "   application/html; ChaRSET='Utf-8'"
        content_type = ContentType.parse(header_value)
        assert content_type.mime == MimeType.html
        assert content_type.charset == "utf-8"

    def test_single_quote_charset(self):
        header_value = "   application/html; ChaRSET='Utf-8'"
        content_type = ContentType.parse(header_value)
        assert content_type.mime == MimeType.html
        assert content_type.charset == "utf-8"

    def test_double_quote_charset(self):
        header_value = 'application/html; ChaRSET="Utf-8"'
        content_type = ContentType.parse(header_value)
        assert content_type.mime == MimeType.html
        assert content_type.charset == "utf-8"

    def test_unquote_charset(self):
        header_value = "application/html; ChaRSET=UTF-8"
        content_type = ContentType.parse(header_value)
        assert content_type.mime == MimeType.html
        assert content_type.charset == "utf-8"

    def test_without_charset(self):
        header_value = "application/html"
        content_type = ContentType.parse(header_value)
        assert content_type.mime == MimeType.html
        assert content_type.charset is None
