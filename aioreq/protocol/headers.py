"""
Contains Header classes to simplify header sending
"""

from collections.abc import Collection
from abc import ABCMeta
from abc import abstractmethod
from abc import ABC
from enum import Enum

def qvalue_validate(qvalue: int) -> bool:
    if 0 <= qvalue <= 1:
        return True
    return False

class ContentCoding(Enum):
    gzip = 'gzip'
    compress = 'compress'
    deflate = 'deflate'
    identity = 'identity'
    all = '*'

class MimeType(Enum):
    json = 'application/json'
    html = 'application/html'

class Header(ABC):

    key = 'NotImplemented'

    @property
    @abstractmethod
    def value(self) -> str:
        ...

class AcceptEncoding(Header):
    """
    RFC[2616] 14.3
        Accept-Encoding request-header field is similar to Accept, but
        restricts the content-codings (section 3.5) that are acceptable in
        the response.
    """

    key = 'Accept-Encoding'

    def __init__(
            self,
            codings: Collection[
                tuple[ContentCoding, int]
                | tuple[ContentCoding],
                ]):
        self._codings = {}
        for coding in codings:
            assert 0 < len(coding) < 3
            if len(coding) == 2:
                coding_type, qvalue = coding # type: ignore
            else:
                coding_type = coding[0]
                qvalue = 1

            if not qvalue_validate(qvalue):
                raise ValueError("Invalid qvalue given -> {qvalue}. Expected int between 0, 1")
            self. _codings[coding_type.value] = qvalue

    @property
    def value(self):
        text = f'Accept-Encoding: '
        for coding, qvalue in self._codings.items():
            text+=f"{coding}; q={qvalue}, "
        if self._codings:
            text = text[:-2]
        return text

class Accept(Header):
    """
    RFC[2616] 14.1
        The Accept request-header field can be used to specify certain media
        types which are acceptable for the response. Accept headers can be
        used to indicate that the request is specifically limited to a small
        set of desired types, as in the case of a request for an in-line image.
    """

    key = 'Accept'

    def __init__(
            self,
            types = Collection[
                tuple[
                    MimeType,
                    int | None
                    ] |
                tuple[
                    MimeType
                    ]
                ]
            ):
         
        self.media_ranges = {}
        for media_range in types:
            assert 0 < len(media_range) < 3
            if len(media_range) == 2:
                type, qvalue = media_range
            else:
                type ,= media_range
                qvalue = 1
            self.media_ranges[type] = qvalue
    
    @property
    def value(self) -> str:
        text = f'{self.key}: '
        for type, qvalue in self.media_ranges.items():
            text+=f'{type.value}; q={qvalue}, '
        text = text[:-2]
        return text


