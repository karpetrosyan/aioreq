from rfcparser.core import SetCookieParser6265, UriParser3986
from rfcparser.object_abstractions import Cookie6265

from aioreq.protocol.cookies import Cookies


def test_remove_cookie():
    uri = UriParser3986().parse("https://example.com")
    cookie_storage = Cookies()
    cookie = Cookie6265(key="test", value="test", uri=uri, attrs={})

    cookie_storage.add_cookie(cookie)

    cookie_storage.get_raw_cookies(123)
    assert cookie_storage.cookies == []

    cookie = SetCookieParser6265().parse("test=test; Max-Age=10", uri=uri)
    cookie_storage.add_cookie(cookie)
    cookie = SetCookieParser6265().parse("test1=test1; Max-Age=10", uri=uri)
    cookie_storage.add_cookie(cookie)
    assert len(cookie_storage.cookies) == 2
    cookie = SetCookieParser6265().parse("test1=newtest; Max-Age=10", uri=uri)
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
    cookie = SetCookieParser6265().parse("test=test; Max-Age=55", uri=uri)
    cookie_storage.add_cookie(cookie)
    raw_cookies = cookie_storage.get_raw_cookies(uri)
    assert raw_cookies == "test=test"

    cookie = SetCookieParser6265().parse("test=test; Max-Age=55; Path=/asdf", uri=uri)
    cookie_storage.add_cookie(cookie)
    raw_cookies = cookie_storage.get_raw_cookies(uri)
    assert raw_cookies == "test=test"

    cookie = SetCookieParser6265().parse("lasttest=test; Max-Age=55", uri=uri)
    cookie_storage.add_cookie(cookie)
    raw_cookies = cookie_storage.get_raw_cookies(uri)
    cookie_storage.add_cookie(cookie)
    assert raw_cookies == "test=test; lasttest=test"

    uri = UriParser3986().parse("https://example.com/random_path/")
    cookie = SetCookieParser6265().parse("mytest=test; Max-Age=55", uri)
    cookie_storage.add_cookie(cookie)
    uri = UriParser3986().parse("https://example.com")
    raw_cookies = cookie_storage.get_raw_cookies(uri)
    assert "mytest" not in raw_cookies
