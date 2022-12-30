import zlib
import gzip as _gzip

from enum import Enum
from abc import ABC
from abc import abstractmethod


class Encoding(ABC):
    all_encodings = []

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
    # Some meta programming :)
    global cls
    for cls in Encoding.all_encodings:
        locals()[cls.__name__] = cls

    def decompress(self, text: bytes) -> bytes:
        return self.value.decompress(text)


def get_avaliable_encodings():
    from .headers import AcceptEncoding
    return AcceptEncoding(
        *((encoding, 1) for encoding in Encoding.all_encodings)
    )
