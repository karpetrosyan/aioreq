import gzip as _gzip

from enum import Enum
from abc import ABC
from abc import abstractmethod 

class Encoding(ABC):
    
    @classmethod
    @abstractmethod
    def decompress(cls, text: bytes) -> bytes:
        ...

class gzip(Encoding):

    @classmethod
    def decompress(cls, text: bytes) -> bytes:
        return _gzip.decompress(text) 

class compress(Encoding):

    @classmethod
    def decompress(cls, text: bytes) -> bytes:
        ...

class Encodings(Enum):
    gzip = gzip
    compress = compress

    def decompress(self, text: bytes) -> bytes:
        return self.value.decompress(text)






