import gzip as _gzip
import zlib
from abc import ABC
from abc import abstractmethod
from enum import Enum
from typing import List
from typing import Type
from typing import TypeVar
from typing import Union

E_TYPE = TypeVar("E_TYPE", bound="Encoding")
import logging

from ..settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)


class Encoding(ABC):
    all_encodings: List[Union[Type["Encoding"], "Encodings"]] = []

    @classmethod
    @abstractmethod
    def decompress(cls, text: bytes) -> bytes:
        ...

    def __init_subclass__(cls):
        Encoding.all_encodings.append(cls)

    @classmethod
    def stringify(cls) -> str:
        return cls.__name__


# Encodings
# -------------


class gzip(Encoding):
    @classmethod
    def decompress(cls, text: bytes) -> bytes:
        return _gzip.decompress(text)


class deflate(Encoding):
    @classmethod
    def decompress(cls, text: bytes) -> bytes:
        decompress = zlib.decompressobj(-zlib.MAX_WBITS)
        inflated = decompress.decompress(text)
        inflated += decompress.flush()
        return inflated


class Encodings(Enum):
    gzip = gzip
    deflate = deflate

    def decompress(self, text: bytes) -> bytes:
        return self.value.decompress(text)


def get_avaliable_encodings():
    from .headers import AcceptEncoding

    encodings = tuple((encoding, 1) for encoding in Encoding.all_encodings)
    return AcceptEncoding(encodings[0])
