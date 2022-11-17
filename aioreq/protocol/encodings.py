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


# class compress(Encoding):
#
#     @classmethod
#     def decompress(cls, text: bytes) -> bytes:
#         raise NotImplementedError


# Enum for encodings
# -------------

class Encodings(Enum):
    gzip = gzip
    # compress = compress

    def decompress(self, text: bytes) -> bytes:
        return self.value.decompress(text)
