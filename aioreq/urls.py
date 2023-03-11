import ipaddress
import re
from typing import Dict
from typing import Optional


def parse_url(url: str) -> "Uri3986":
    return UriParser3986().parse(url)


class Uri3986:
    def __init__(
        self,
        scheme: str,
        ip: Optional[str],
        port: Optional[int],
        host,
        userinfo: Optional[str],
        path: Optional[str],
        query: Dict[str, str],
        fragment: Optional[str],
    ):
        self.scheme = scheme
        self.ip = ip
        self.port = port
        self.host = host
        self.userinfo = userinfo
        self._path = path
        self.query = query
        self.fragment = fragment

    def updated_relative_ref(self, value: str) -> str:
        if value.startswith("//"):
            value = f"{self.scheme}:{value}"
        else:
            userinfo = f"{self.userinfo}@" if self.userinfo else ""
            hostname = self.ip or ".".join(self.host)
            port = f":{self.port}" if self.port else ""
            value = f"{self.scheme}://{userinfo}{hostname}{port}{value}"
        return value

    @property
    def path(self) -> Optional[str]:
        return self._path

    @path.setter
    def path(self, newvalue: str) -> None:
        if newvalue and not newvalue.startswith("/"):
            newvalue = "/" + newvalue
        self._path = newvalue

    def ignored_query_and_path(self) -> str:
        hostname = self.ip or ".".join(self.host)
        port = f":{self.port}" if self.port else ""
        userinfo = f"{self.userinfo}@" if self.userinfo else ""
        fragment = f"#{self.fragment}" if self.fragment else ""
        return f"{self.scheme}://{userinfo}{hostname}{port}{fragment}"

    def path_and_query(self) -> str:
        path = self.path if self.path else "/"
        attrs = (
            ("?" + "&".join([f"{key}={value}" for key, value in self.query.items()]))
            if self.query
            else ""
        )
        return path + attrs

    def get_domain(self) -> str:
        if self.ip:
            return self.ip
        return ".".join(self.host)

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError()

        return all(
            (
                self.scheme == other.scheme,
                self.ip == other.ip,
                self.port == other.port,
                self.host == other.host,
                self.userinfo == other.userinfo,
                self.path == other.path,
                self.query == other.query,
                self.fragment == other.fragment,
            )
        )

    def __str__(self) -> str:
        hostname = self.ip or ".".join(self.host)
        port = f":{self.port}" if self.port else ""
        path = self.path if self.path else "/"
        userinfo = f"{self.userinfo}@" if self.userinfo else ""
        fragment = f"#{self.fragment}" if self.fragment else ""
        attrs = (
            ("?" + "&".join([f"{key}={value}" for key, value in self.query.items()]))
            if self.query
            else ""
        )
        return f"{self.scheme}://{userinfo}{hostname}{port}{path}{attrs}{fragment}"

    def __repr__(self):
        return f"<Uri3986 {str(self)}>"


class UriParser3986:
    uri_parsing_regex = re.compile(
        r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?"
    )

    def parse(self, value: str) -> Uri3986:
        match = self.uri_parsing_regex.search(value)
        msg = (
            "Invalid uri was passed through `UriParser`.\n"
            "Valid uri examples: [http://127.0.0.1:443, https://google.com]"
        )
        if not match:
            raise ValueError(msg)

        query_dict = {}
        scheme = match.group(2)
        authority = match.group(4)
        path = match.group(5)
        query = match.group(7)
        fragment = match.group(9)
        if scheme not in ("https", "http"):
            raise ValueError(msg)

        if not authority or not scheme:
            raise ValueError(msg)
        sep_ind = authority.find("@")
        if sep_ind != -1:
            userinfo = authority[:sep_ind]
            authority = authority[sep_ind + 1 :]
        else:
            userinfo = None

        sep_ind = authority.find(":")
        if sep_ind != -1:
            port = int(authority[sep_ind + 1 :])
            authority = authority[:sep_ind]
        else:
            port = None

        host = authority
        try:
            ipaddress.ip_address(host)
            ip = host
            host = None
        except ValueError:
            ip = None

        if query:
            for key_value in query.split("&"):
                key, value = key_value.split("=")
                query_dict[key] = value

        if host:
            host = host.split(".")

        return Uri3986(
            scheme=scheme,
            ip=ip,
            port=int(port) if port else None,
            host=host,
            userinfo=userinfo,
            path=path,
            query=query_dict,
            fragment=fragment,
        )
