from .headers import Cookie


class Cookies:
    def __init__(self, cookies=None):
        if cookies is None:
            cookies = {}
        if not isinstance(cookies, dict):
            raise ValueError(
                f"First parameter {self.__class__.__name__} accepts only dictionary"
            )
        self._cookies = cookies
        self.cache = None

    @property
    def cookies(self):
        return self._cookies

    def add_cookie(self, set_cookie):
        self.cache = None
        self.cookies[set_cookie.key] = set_cookie

    def get_cookie(self, key):
        if key not in self._cookies:
            raise ValueError(f"Key: {key} does not exists")
        return self._cookies[key]

    def get_raw_cookies(self):
        if self.cache:
            return self.cache
        header = Cookie(self.cookies)
        return header.value

    def __repr__(self):
        return f"<Cookie: {self.get_raw_cookies()}>"
