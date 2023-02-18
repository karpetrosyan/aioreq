import pytest

from aioreq.urls import Uri3986
from aioreq.urls import UriParser3986


class TestUri3986:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (
                "http://example.com",
                Uri3986(
                    scheme="http",
                    ip=None,
                    port=None,
                    host=["example", "com"],
                    userinfo=None,
                    path="",
                    query={},
                    fragment=None,
                ),
            ),
            (
                "https://127.0.0.1/path?name=test#fr",
                Uri3986(
                    scheme="https",
                    ip="127.0.0.1",
                    port=None,
                    host=None,
                    userinfo=None,
                    path="/path",
                    query={"name": "test"},
                    fragment="fr",
                ),
            ),
            (
                "https://testdata@127.0.0.1:1010/path?name=test#fr",
                Uri3986(
                    scheme="https",
                    ip="127.0.0.1",
                    port=1010,
                    host=None,
                    userinfo="testdata",
                    path="/path",
                    query={"name": "test"},
                    fragment="fr",
                ),
            ),
        ],
    )
    def test_parsing(self, value, expected):
        parsed = UriParser3986().parse(value)

        assert parsed.scheme == expected.scheme
        assert parsed.ip == expected.ip
        assert parsed.port == expected.port
        assert parsed.host == expected.host
        assert parsed.userinfo == expected.userinfo
        assert parsed.path == expected.path
        assert parsed.query == expected.query
        assert parsed.fragment == expected.fragment
        assert parsed == expected

    @pytest.mark.parametrize(
        "value, newvalue, expected",
        [
            (
                UriParser3986().parse("https://google.com/path?name=test"),
                "/new/path",
                "https://google.com/new/path?name=test",
            ),
            (
                UriParser3986().parse("https://google.com/path?name=test"),
                "new/path",
                "https://google.com/new/path?name=test",
            ),
            (
                UriParser3986().parse("https://google.com/path?name=test"),
                "",
                "https://google.com/?name=test",
            ),
        ],
    )
    def test_update_path(self, value, newvalue, expected):
        value.path = newvalue
        assert str(value) == expected

    @pytest.mark.parametrize(
        "value, newvalue, expected",
        [
            (
                UriParser3986().parse("https://google.com/path?name=test"),
                "//test.com/path?name=test",
                "https://test.com/path?name=test",
            ),
            (
                UriParser3986().parse("https://google.com/path?name=test"),
                "/newpath#asd",
                "https://google.com/newpath#asd",
            ),
        ],
    )
    def test_update_relative_path(self, value, newvalue, expected):
        new_value = value.updated_relative_ref(newvalue)
        assert new_value == expected

    @pytest.mark.parametrize(
        argnames=["url"],
        argvalues=[
            ("google.com",),
            ("/google.com",),
            ("httd//google.com",),
            ("htt//google.com",),
        ],
    )
    def test_invalid_urls(self, url):
        with pytest.raises(ValueError, match=("Invalid uri was passed through .*")):
            UriParser3986().parse(url)
