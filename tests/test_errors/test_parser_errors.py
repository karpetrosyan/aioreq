import pytest

from aioreq.errors.parser import UrlParsingError


def test_domain_syntax_error():
    (text,) = UrlParsingError("https://asdfgasd/asdgasdgoj?asdf1=12").args
    assert text == "Unexpected domain syntax."


def test_http_scheme_missing_error():
    (text,) = UrlParsingError("htp://example.com").args
    assert text == "Url should starts with `http://` or `https://`."


def test_url_parts_missing_error():
    (text,) = UrlParsingError("http://./").args
    assert text == "Missing url parts: ('Domain', 'Top-level-domain')"

    (text,) = UrlParsingError("http://.topdomain/").args
    assert text == "Missing url part: Domain"

    (text,) = UrlParsingError("http://domain./").args
    assert text == "Missing url part: Top-level-domain"
