import pytest

from aioreq.parser.url_parser import UrlParser


class TestUrlParser:
    """
    Check if url parser works correctly.
    
    Parser path is aioreq.parser.url_parser.UrlParser
    which implements all Url parsing logic and returns object
    type of aioreq.parser.url_parser.Url
    """

    @pytest.mark.parametrize(
        argnames=['url', 'protocol', 'subdomain', 'domain',
                  'top_level_domain', 'path', 'variables', 'fragment'],
        argvalues=[
            ("https://www.youtube.com", 'https', "www", "youtube", "com", "/", None, None),
            ("http://test.google.ru/", "http", "test", "google", "ru", "/", None, None),
            ("https://test.test.test/path_example", "https", "test", "test", "test", "/path_example", None, None),
            ("https://test.test.test/path/pathtwo/pathtree", "https", "test", "test", "test", "/path/pathtwo/pathtree",
             None, None),
            ("https://test.test.test/path?a=2&f=3&f=4", "https", "test", "test", "test", "/path", "a=2&f=3&f=4", None),
            ("https://test.test.test/path?a=2&f=3&f=4#testfragment", "https", "test", "test", "test", "/path",
             "a=2&f=3&f=4", "testfragment"),
            ("https://test.test.test/?a=2&f=3&f=4#testfragment", "https", "test", "test", "test", '/', "a=2&f=3&f=4",
             "testfragment"),
            ("https://test.test.test/#testfragment", "https", "test", "test", "test", '/', None, "testfragment"),
            (
            "https://test.test.test/pathone/pathtwo/pathtree?a=2&c=3&l=3#testfragment", "https", "test", "test", "test",
            "/pathone/pathtwo/pathtree", "a=2&c=3&l=3", "testfragment"),
        ]
    )
    def test_url_parsing(
            self,
            url,
            protocol,
            subdomain,
            domain,
            top_level_domain,
            path,
            variables,
            fragment
    ):
        """
        Check if UrlParser parses raw url text correctly
        """

        url_object = UrlParser.parse(url)

        assert url_object.protocol == protocol
        assert url_object.domain == domain
        assert url_object.subdomain == subdomain
        assert url_object.top_level_domain == top_level_domain
        assert url_object.path == path
        assert url_object.variables == variables
        assert url_object.fragment == fragment
