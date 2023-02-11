"""
Contains Header classes to simplify header sending
"""
import logging
from abc import ABC
from abc import abstractmethod
from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

from aioreq.cookies import Cookie6265
from aioreq.cookies import default_path
from aioreq.parsers import DateParser6265
from aioreq.settings import LOGGER_NAME

from .encodings import Encoding
from .encodings import Encodings

log = logging.getLogger(LOGGER_NAME)

T = TypeVar("T", bound="Headers")


class MetaHeaders(type):
    def __call__(cls, initial_headers=None):
        """
        If 'initial headers' passed through 'Headers' is already an instance of 'Headers,'
        return it rather than creating a new one.
        """
        if isinstance(initial_headers, Headers):
            return initial_headers
        return super(MetaHeaders, cls).__call__(initial_headers)


class Headers(metaclass=MetaHeaders):
    multivalue_headers = frozenset(("set-cookie", "www-authenticate"))

    def __init__(self, initial_headers: Optional[Union[Dict[str, str], T]] = None):
        self._headers: Dict[str, Union[str, List]] = {}
        self.cache: Optional[str] = ""

        if initial_headers:
            for key, value in initial_headers.items():
                self[key] = value

    def __setitem__(self, key: str, value: str):

        self.cache = None
        key = key.lower()
        if key in self.multivalue_headers:
            values = self._headers.setdefault(key, [])
            values.append(value)
        else:
            self._headers[key.lower()] = value

    def __getitem__(self, item):
        return self._headers[item.lower()]

    def add_header(self, header: "BaseHeader"):
        self[header.key] = header.value

    def get_parsed(self):
        if self.cache is not None:
            return self.cache

        headers = (
                "\r\n".join(f"{key}:  {value}" for key, value in self._headers.items())
                + "\r\n"
        )
        self.cache = headers
        return headers

    def items(self):
        return self._headers.items()

    def get(self, name, default=None):
        return self._headers.get(name.lower(), default)

    def dict(self):
        return self._headers

    def __contains__(self, item):
        return item.lower() in self._headers

    def __or__(self, other):
        if not isinstance(other, Headers):
            raise ValueError(
                f"Can't combine {self.__class__.__name__} object with {type(other).__name__}"
            )

        self._headers.update(other._headers)
        return Headers(initial_headers=self._headers)

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if len(self._headers) != len(other.dict()):
            return False
        for header in self._headers:
            if header not in other.dict() or (
                    header and other.dict()[header] != self._headers[header]
            ):
                return False
        return True

    def __len__(self):
        return len(self._headers)

    def __repr__(self):
        return f"Headers:\n" + "\n".join(
            (f" {key}: {value}" for key, value in self._headers.items())
        )


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

    def __init__(self):
        self.auth_schemes: Dict[str, dict] = {}

    @classmethod
    def parse(cls, values: List[str]):

        self = cls()
        for value in values:
            cleaned_attrs = {}
            sp_ind = value.find(" ")
            if sp_ind != -1:
                auth_scheme = value[:sp_ind]
                value = value[sp_ind + 1:]
            else:
                auth_scheme = value

            attrs = value.split(',')
            for attr in attrs:
                attr = attr.strip()
                key, value = attr.split("=")
                key = key.strip()
                value = value.strip()
                cleaned_attrs[key] = value
            self.auth_schemes[auth_scheme] = cleaned_attrs
        return self

    def __repr__(self):
        return f"<AuthenticationWWW {self.auth_schemes}>"


class SetCookie(ServerHeader):
    def _validate(self, attrs, uri):
        cleaned_attrs = {}

        for attribute_name, attribute_value in attrs.items():
            if attribute_name.lower() == "expires":
                try:
                    expiry_time = DateParser6265().parse(attribute_value)
                except Exception:
                    continue
                cleaned_attrs["Expires"] = expiry_time

            elif attribute_name.lower() == "max-age":
                brk = False
                if not (attribute_value[0].isdigit() or attribute_value[0] == "="):
                    continue

                for char in attribute_value:
                    if not char.isdigit():
                        brk = True
                        continue
                if brk:
                    continue
                delta_seconds = int(attribute_value)
                if delta_seconds <= 0:
                    expiry_time = datetime.now()
                else:
                    expiry_time = datetime.now() + timedelta(seconds=delta_seconds)
                cleaned_attrs["Max-Age"] = expiry_time

            elif attribute_name.lower() == "domain":
                if not attribute_value:
                    continue

                if attribute_value[0] == ".":
                    cookie_domain = attribute_value[1:]
                else:
                    cookie_domain = attribute_value
                cookie_domain = cookie_domain.lower()
                cleaned_attrs["Domain"] = cookie_domain

            elif attribute_name.lower() == "path":
                if (not attribute_value) or (attribute_value[0] != "/"):
                    cookie_path = default_path(uri)
                else:
                    cookie_path = attribute_value
                cleaned_attrs["Path"] = cookie_path

            elif attribute_name.lower() == "secure":
                cleaned_attrs["Secure"] = ""
            elif attribute_name.lower() == "httponly":
                cleaned_attrs["HttpOnly"] = ""

        return cleaned_attrs

    def parse(self, value, uri):
        if ";" in value:
            name_value_pair = value.split(";")[0]
            unparsed_attributes = value[value.find(";"):]
        else:
            name_value_pair = value
            unparsed_attributes = ""
        eq_ind = name_value_pair.find("=")
        if eq_ind == -1:
            return None
        name = name_value_pair[:eq_ind].strip()
        value = name_value_pair[eq_ind + 1:].strip()
        attrs = {}

        if not name:
            raise None

        while unparsed_attributes:
            unparsed_attributes = unparsed_attributes[1:]
            sep_ind = unparsed_attributes.find(";")
            if sep_ind != -1:
                cookie_av = unparsed_attributes[:sep_ind]
            else:
                cookie_av = unparsed_attributes
            eq_ind = cookie_av.find("=")
            if eq_ind != -1:
                attribute_name = cookie_av[:eq_ind]
                attribute_value = cookie_av[eq_ind + 1:]
            else:
                attribute_name = cookie_av
                attribute_value = ""
            attribute_name = attribute_name.strip()
            attribute_value = attribute_value.strip()
            attrs[attribute_name] = attribute_value
            unparsed_attributes = unparsed_attributes[sep_ind:]

        cleaned_attrs = self._validate(attrs, uri)
        try:
            return Cookie6265(key=name, value=value, uri=uri, attrs=cleaned_attrs)
        except ValueError:
            return None


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
