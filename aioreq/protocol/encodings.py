import zlib
import base64
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
        decoded_data = base64.b64decode(text)
        res = zlib.decompress(decoded_data, -15)
        return res


class Encodings(Enum):
    # Some meta programming :)
    global cls
    for cls in Encoding.all_encodings:
        locals()[cls.__name__] = cls

    def decompress(self, text: bytes) -> bytes:
        return self.value.decompress(text)
