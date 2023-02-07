import datetime

from rfcparser.object_abstractions import path_matches


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
                and path_matches(uri.get_domain(), cookie.domain)
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
            cookie.last_access_time = datetime.datetime.now()

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
            if datetime.datetime.now() <= cookie.expiry_time:
                new_cookies.append(cookie)

        self._cookies = new_cookies

    def get_raw_cookies(self, uri):
        self.remove_expired_cookies()
        return self._get_cookie_string(uri)

    def __repr__(self):
        raw_cookies = self.get_raw_cookies()
        return f"<Cookie: {raw_cookies}>"
