"""
Contains Header classes to simplify header sending
"""
from abc import ABC
from abc import abstractmethod
from enum import Enum
from typing import Dict, List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union
from datetime import datetime

from lark import Lark

from .encodings import Encoding
from .encodings import Encodings


def qvalue_validate(qvalue: int) -> bool:
    return 0 <= qvalue <= 1


class MimeType(Enum):
    json = "application/json"
    html = "application/html"
    audio = "audio/aac"
    abiword = "application/x-abiword"
    archive = "application/x-freearc"
    avif = "image/avif"
    avl = "video/x-msvideo"
    kindle_ebook = "application/vnd.amazon.ebook"
    binary = "application/octet-stream"
    bmp = "image/bmp"
    css = "text/css"
    csv = "text/csv"
    gzip = "application/gzip"
    gif = "image/gif"
    js = "text/javascript"
    png = "image/png"


class ServerHeader(ABC):
    @classmethod
    @abstractmethod
    def parse(self, value: str):
        ...


class BaseHeader(ABC):
    key = "NotImplemented"

    @property
    @abstractmethod
    def value(self) -> str:
        ...


class AcceptEncoding(BaseHeader):
    """
    RFC[2616] 14.3
        Accept-Encoding request-header field is similar to Accept, but
        restricts the content-codings (section 3.5) that are acceptable in
        the response.
    """

    key = "Accept-Encoding"

    def __init__(
            self, *codings: Tuple[Union[Type[Encoding], Encodings], Union[None, int]]
    ):
        self._codings: Dict[str, str] = {}
        for coding in codings:
            coding_type, qvalue = coding  # type: ignore

            if qvalue is not None:
                if not qvalue_validate(qvalue):
                    raise ValueError(
                        "Invalid qvalue given -> {qvalue}. Expected number between 0, 1"
                    )
                str_qvalue = str(qvalue)
            else:
                str_qvalue = "1"

            if isinstance(coding_type, Encodings):
                self._codings[coding_type.value.stringify()] = str_qvalue
            else:
                self._codings[coding_type.stringify()] = str_qvalue

    @property
    def value(self):
        text = " "
        for coding, qvalue in self._codings.items():
            text += f"{str(coding)}; q={qvalue}, "
        if self._codings:
            text = text[:-2]
        return text


class Accept(BaseHeader):
    """
    RFC[2616] 14.1
        The Accept request-header field can be used to specify certain media
        types which are acceptable for the response. Accept headers can be
        used to indicate that the request is specifically limited to a small
        set of desired types, as in the case of a request for an in-line image.

    :Example:

    >>> from aioreq.protocol.headers import Accept
    >>> from aioreq.protocol.headers import MimeType
    >>> Accept((MimeType.js, 1), (MimeType.avl, None)).value
    ' text/javascript; q=1, video/x-msvideo; q=1'
    >>> Accept((MimeType.js, 0.5), (MimeType.avl, None)).value
    ' text/javascript; q=0.5, video/x-msvideo; q=1'
    >>> Accept((MimeType.js, 0.5), (MimeType.avl, None), (MimeType.csv, 0.1)).value
    ' text/javascript; q=0.5, video/x-msvideo; q=1, text/csv; q=0.1'
    """

    key = "Accept"

    def __init__(self, *types: Tuple[MimeType, Optional[Union[int, float]]]):

        self.media_ranges: Dict[MimeType, str] = {}
        for media_range in types:
            m_type, qvalue = media_range
            if qvalue is None:
                str_value = "1"
            else:
                str_value = str(qvalue)

            self.media_ranges[m_type] = str_value

    @property
    def value(self) -> str:
        text = " "
        for m_type, qvalue in self.media_ranges.items():
            text += f"{m_type.value}; q={qvalue}, "
        text = text[:-2]
        return text


class ServerEncoding(ServerHeader):
    def __init__(self):
        self.encodings = []
        self.iternum = 0

    @classmethod
    def parse(cls, text: str):
        self = cls()
        encodings = text.split(",")
        for encoding in encodings:
            if encoding != "chunked":
                self.encodings.append(Encodings[encoding.strip()])
        self.encodings.reverse()
        return self

    def __iter__(self):
        self.iternum = 0
        return self

    def __next__(self):
        if self.iternum >= len(self.encodings):
            raise StopIteration
        encoding = self.encodings[self.iternum]
        self.iternum += 1
        return encoding


class TransferEncoding(ServerEncoding):
    ...


class ContentEncoding(ServerEncoding):
    ...


class AuthenticationWWW(ServerHeader):
    """
    RFC[7235] 4.1
        The "WWW-Authenticate" header field indicates the authentication
        scheme(s) and parameters applicable to the target resource.

        WWW-Authenticate = 1#challenge

        A server generating a 401 (Unauthorized) response MUST send a
        WWW-Authenticate header field containing at least one challenge.  A
        server MAY generate a WWW-Authenticate header field in other response
        messages to indicate that supplying credentials (or different
        credentials) might affect the response.
    """

    parser = Lark(
        r"""
            challenge:      auth_scheme params
            !auth_scheme:   "Basic" | "Digest"
            params:         (param COL)* param?
            param:          key EQ value
            key:            /[^=\s]+/
            value:          /\"[^\"]+\"/
            EQ:             "="
            COL:            ","

            %ignore /\s/
            """,
        parser="lalr",
        start="challenge",
    )

    def __init__(self):
        self.auth_schemes: Dict[str, dict] = {}

    @classmethod
    def parse(cls, values: List[str]):
        """
        :Example:

        >>> from aioreq.protocol.headers import AuthenticationWWW
        >>> AuthenticationWWW.parse(['Basic realm="test"', 'Digest realm="asdf"'])
        <AuthenticationWWW {'Basic': {'realm': '"test"'}, 'Digest': {'realm': '"asdf"'}}>
        >>> AuthenticationWWW.parse(['Basic realm="test1", arg1="test2"'])
        <AuthenticationWWW {'Basic': {'realm': '"test1"', 'arg1': '"test2"'}}>
        >>> AuthenticationWWW.parse(['Basic realm="Fake Realm"'])
        <AuthenticationWWW {'Basic': {'realm': '"Fake Realm"'}}>
        """

        self = cls()
        for value in values:
            parsed = self.parser.parse(value)
            params = {}
            scheme = parsed.children[0].children[0].value  # type: ignore

            for param in parsed.children[1].children:  # type: ignore
                if type(param) != type(parsed):
                    continue
                key = param.children[0].children[0].value  # type: ignore
                value = param.children[2].children[0].value  # type: ignore
                params[key] = value
            self.auth_schemes[scheme] = params
        return self

    def __repr__(self):
        return f"<AuthenticationWWW {self.auth_schemes}>"


class SetCookie(ServerHeader):
    parser = Lark(
        r"""
            cookie_string:  cookie_pair (AREND SP cookie_parameter)*
            cookie_pair:    KEY EQ VAL
            cookie_parameter: ATTRIBUTE (EQ VAL)?
            KEY:            /\b[^=;]+/
            VAL:          /[^;]+/
            ATTRIBUTE: "Expires" | "Max-Age" | "Domain" | "Path" | "Secure" | "HttpOnly" | "SameSite" | "Partitioned"
                        | "expires" | "max-age" | "domain" | "path" | "secure" | "httponly" | "samesite" | "partitioned"
            EQ:             "="
            AREND:          ";"
            COL:            ","
            SP:             " "
        """,
        parser="lalr",
        start="cookie_string",
    )

    datetime_formats = frozenset((
        ('rfc850', "%a, %d %b %Y %H:%M:%S %Z"),  # Sun, 06 Nov 1994 08:49:37 GMT
        ('rfc822', "%A, %d-%b-%y %H:%M:%S %Z"),  # Sunday, 06-Nov-94 08:49:37 GMT
        ('undefined', "%a, %d-%b-%Y %H:%M:%S %Z")
    ))

    def __init__(self):
        self.key = None
        self.value = None
        self.attrs = {}

    @classmethod
    def parse_datetime(cls, value):
        for rfc, date_format in cls.datetime_formats:
            try:
                return datetime.strptime(value, date_format)
            except Exception:
                ...
        raise ValueError(f"Invalid datetime received from the server {value}")

    @classmethod
    def parse(cls, value: str):
        self = cls()
        parsed_tree = cls.parser.parse(value)

        key = parsed_tree.children[0].children[0].value
        value = parsed_tree.children[0].children[2].value
        self.key = key
        self.value = value
        attrs = self.attrs

        for attr in parsed_tree.find_data("cookie_parameter"):
            if len(attr.children) == 1:
                key, = attr.children
                attrs[key.value] = None
            else:

                key, _, value = attr.children
                if key.value.startswith('exp') or key.value.startswith('Exp'):
                    value.value = cls.parse_datetime(value)
                attrs[key.value] = value.value
        return self

    def __repr__(self):
        return f"<Set-Cookie {self.key}={self.value}>"


class Cookie(BaseHeader):
    def __init__(self, cookies: Dict):
        self.cookies = cookies

    @property
    def value(self) -> str:
        cookie_string = ""

        for key, set_cookie in self.cookies.items():
            keyval = f"{key}={set_cookie.value}; "
            cookie_string += keyval

        if cookie_string:
            cookie_string = cookie_string[:-2]
        return cookie_string
