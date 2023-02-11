from datetime import datetime
from datetime import timedelta

import pytest

from aioreq.cookies import Cookie6265
from aioreq.cookies import Cookies
from aioreq.cookies import path_matches
from aioreq.headers import SetCookie
from aioreq.urls import UriParser3986


def test_remove_cookie():
    uri = UriParser3986().parse("https://example.com")
    cookie_storage = Cookies()
    cookie = Cookie6265(key="test", value="test", uri=uri, attrs={})

    cookie_storage.add_cookie(cookie)

    cookie_storage.get_raw_cookies(123)
    assert cookie_storage.cookies == []

    cookie = SetCookie().parse("test=test; Max-Age=10", uri=uri)
    cookie_storage.add_cookie(cookie)
    cookie = SetCookie().parse("test1=test1; Max-Age=10", uri=uri)
    cookie_storage.add_cookie(cookie)
    assert len(cookie_storage.cookies) == 2
    cookie = SetCookie().parse("test1=newtest; Max-Age=10", uri=uri)
    cookie_storage.add_cookie(cookie)

    for cookie in cookie_storage.cookies:
        if cookie.key == "test1":
            assert cookie.value == "newtest"
            break
    else:
        assert not "Can't find inserted cookie"


def test_cookie_string():
    uri = UriParser3986().parse("https://example.com")
    cookie_storage = Cookies()
    cookie = SetCookie().parse("test=test; Max-Age=55", uri=uri)
    cookie_storage.add_cookie(cookie)
    raw_cookies = cookie_storage.get_raw_cookies(uri)
    assert raw_cookies == "test=test"

    cookie = SetCookie().parse("test=test; Max-Age=55; Path=/asdf", uri=uri)
    cookie_storage.add_cookie(cookie)
    raw_cookies = cookie_storage.get_raw_cookies(uri)
    assert raw_cookies == "test=test"

    cookie = SetCookie().parse("lasttest=test; Max-Age=55", uri=uri)
    cookie_storage.add_cookie(cookie)
    raw_cookies = cookie_storage.get_raw_cookies(uri)
    cookie_storage.add_cookie(cookie)
    assert raw_cookies == "test=test; lasttest=test"

    uri = UriParser3986().parse("https://example.com/random_path/")
    cookie = SetCookie().parse("mytest=test; Max-Age=55", uri)
    cookie_storage.add_cookie(cookie)
    uri = UriParser3986().parse("https://example.com")
    raw_cookies = cookie_storage.get_raw_cookies(uri)
    assert "mytest" not in raw_cookies


@pytest.mark.parametrize(
    "request_path, cookie_path, expected",
    [
        ("/label1/label2", "/label1", True),
        ("/label1/label2", "/label1/", True),
        ("/label1/label2", "/label/", False),
        ("/label1/label2", "/", True),
        ("/label1", "/", True),
        ("/", "/", True),
        ("/a", "/", True),
    ],
)
def test_path_matches(request_path, cookie_path, expected):
    assert path_matches(request_path, cookie_path) == expected


def test_expiry_time():
    uri = UriParser3986().parse("https://example.com")
    expiry_time = datetime.now() + timedelta(minutes=123123)
    attrs = {"Max-Age": 20, "HttpOnly": True, "Expires": expiry_time}
    cookie = Cookie6265(key="test", value="test", uri=uri, attrs=attrs)
    assert cookie.expiry_time != expiry_time
