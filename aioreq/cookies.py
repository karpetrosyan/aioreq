import ipaddress
from datetime import datetime


def default_path(uri):
    uri_path = uri.path

    if not uri_path or uri_path[0] != "/":
        return "/"
    if uri_path.count("/") == 1:
        return "/"
    assert len("".join(uri_path.split("/")[:-1]))

    if uri_path.endswith("/"):
        return uri_path[:-1]
    return uri_path


def path_matches(request_path, cookie_path):
    if request_path == "":
        request_path = "/"

    if request_path == cookie_path:
        return True

    if len(request_path) > len(cookie_path) and request_path.startswith(cookie_path):
        if cookie_path[-1] == "/":
            #   The cookie-path is a prefix of the request-path, and the last
            # 	character of the cookie-path is %x2F ("/").
            return True
        if request_path[0] == "/":
            #   The cookie-path is a prefix of the request-path, and the
            #   first character of the request-path that is not included in
            #   the cookie-path is a %x2F ("/") character.
            return True
    return False


def domain_matches(string: str, domain_string: str) -> bool:
    string = string.lower()
    domain_string = domain_string.lower()
    try:
        ipaddress.ip_address(string)
        is_host = False
    except ValueError:
        is_host = True
    return string == domain_string or (
        string.endswith(domain_string)
        and string[-(len(domain_string) + 1)] == "."
        and is_host
    )


class Cookie6265:
    def __init__(self, key, value, uri, attrs):
        self.key = key
        self.value = value
        self.creation_time = self.last_access_time = datetime.now()
        self.persistent_flag = False
        self.expiry_time = None
        self.domain = attrs.get("Domain", "")

        if self.domain:
            if not domain_matches(uri.get_domain(), self.domain):
                raise ValueError()
            else:
                self.host_only_flag = False
        else:
            self.host_only_flag = True
            self.domain = uri.get_domain()

        max_age = attrs.get("Max-Age", None)
        if max_age is not None:
            self.persistent_flag = True
            self.expiry_time = max_age
        else:
            expires = attrs.get("Expires", None)
            if expires:
                self.persistent_flag = True
                self.expiry_time = expires
            else:
                self.persistent_flag = False
                self.expiry_time = datetime.now()

        path = attrs.get("Path", None)
        if path:
            self.path = path
        else:
            self.path = default_path(uri)
        self.secure_only_flag = "Secure" in attrs
        self.http_only_flag = "HttpOnly" in attrs

    def __str__(self):
        return f"{self.key}={self.value}"

    def __repr__(self):
        return f"<SetCookie6265 {str(self)}"


class Cookies:
    def __init__(self):
        self._cookies = []
        self.cache = None

    @property
    def cookies(self):
        return self._cookies

    def _remove_cookie(self, cookie):
        self._cookies.remove(cookie)

    def _get_cookie_string(self, uri):
        """
        RFC 6265 -> 5.4
        """
        cookie_list = []

        for cookie in self._cookies:
            # Let cookie-list be the set of cookies from the cookie store that
            #                 meets all of the following requirements:

            #   Either:
            #       The cookie's host-only-flag is true and the canonicalized
            #       request-host is identical to the cookie's domain.
            #   Or:
            #       The cookie's host-only-flag is false and the canonicalized
            #       request-host domain-matches the cookie's domain.

            if not (
                cookie.host_only_flag
                and cookie.domain == uri.get_domain()
                or cookie.host_only_flag
                and domain_matches(uri.get_domain(), cookie.domain)
            ):
                continue

            #   The request-uri's path path-matches the cookie's path
            if not (path_matches(uri.path, cookie.path)):
                continue

            #   If the cookie's http-only-flag is true, then exclude the
            #   cookie if the cookie-string is being generated for a "non-
            #   HTTP" API (as defined by the user agent).
            if cookie.secure_only_flag and not uri.scheme.startswith("https"):
                continue
            cookie_list.append(cookie)

        #   The user agent SHOULD sort the cookie-list in the following
        #   order:
        #       *  Cookies with longer paths are listed before cookies with
        #          shorter paths.
        #       *  Among cookies that have equal-length path fields, cookies with
        #           earlier creation-times are listed before cookies with later
        #           creation-times.
        cookie_list.sort(key=lambda cookie: (-len(cookie.path), cookie.creation_time))

        #   Update the last-access-time of each cookie in the cookie-list to
        #   the current date and time.
        for cookie in cookie_list:
            cookie.last_access_time = datetime.now()

        #   Serialize the cookie-list into a cookie-string by processing each
        #        cookie in the cookie-list in order:
        #       1.  Output the cookie's name, the %x3D ("=") character, and the
        #            cookie's value.
        #
        #       2.  If there is an unprocessed cookie in the cookie-list, output
        #            the characters %x3B and %x20 ("; ").
        cookie_string = "; ".join(
            f"{cookie.key}={cookie.value}" for cookie in cookie_list
        )
        return cookie_string

    def cookie_exists(self, set_cookie):
        key = set_cookie.key
        domain = set_cookie.domain
        path = set_cookie.path

        for cookie in self._cookies:
            if cookie.key == key and cookie.domain == domain and cookie.path == path:
                return cookie
        return False

    def add_cookie(self, cookie):
        self.remove_expired_cookies()
        old_cookie = self.cookie_exists(cookie)
        if old_cookie:
            cookie.creation_time = old_cookie.creation_time
            self._remove_cookie(old_cookie)
        self._cookies.append(cookie)

    def remove_expired_cookies(self):
        new_cookies = []
        for cookie in self._cookies:
            if datetime.now() <= cookie.expiry_time:
                new_cookies.append(cookie)

        self._cookies = new_cookies

    def get_raw_cookies(self, uri):
        self.remove_expired_cookies()
        return self._get_cookie_string(uri)

    def __repr__(self):
        raw_cookies = self.get_raw_cookies()
        return f"<Cookie: {raw_cookies}>"
