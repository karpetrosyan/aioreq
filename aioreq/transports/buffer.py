import logging
from abc import abstractmethod, ABC

from enum import Enum
from ..settings import LOGGER_NAME
from ..parser.response_parser import ResponseParser

from typing import Tuple

log = logging.getLogger(LOGGER_NAME)


class ResponseParserStrategy(Enum):
    """
    An enumeration that implements the strategy design pattern used to
    choice of method for parsing the answer.
    """
    chunked = 'chunked'
    content_length = 'content_length'

    @staticmethod
    def parse_content_length(buffer: 'Buffer') -> bytes | None:
        """
        Parse incoming `BaseBuffer` object receiving data on which body length by `content-length` header.

        RFC[2616] 14.13 Content-Length:
            The Content-Lenght entity-header field indicates the size of the entity-body,
            in decimal number of OCTETs, sent to the recipent or, in the case of the HEAD method,
            the size of the entity-body that would have been sent had the request been a GET
        :param buffer: A buffer which data should be parsed
        :type buffer: BaseBuffer
        :return: Parsed and verified HTTP response or `NoneType` object
        """

        if len(buffer.text) >= buffer.content_length:
            buffer.switch_data(buffer.content_length)
            return buffer.message_verify()
        return None

    @staticmethod
    def parse_chunked(buffer: 'Buffer') -> None | bytes:
        """
        Parse incoming `BaseBuffer` object receiving data on which body length by chunked transfer encoding.

        RFC[2616] 3.6.1 Chunked Transfer Coding:
            The chunked encoding modifies the body of a message in order to transfer it as a series of
            chunkd, each with its own size indicator, followed by an OPTIONAL trailer containing entity-header
            fields. This allows dynamically produced content to be transferred along with the information
            necessary for the recipient to verify that it has received the full message
        :param buffer: A buffer which data should be parsed
        :type buffer: BaseBuffer
        :return: Parsed and verified HTTP response or `NoneType` object
        """

        while True:
            if buffer.bytes_should_receive_and_save:
                if buffer.bytes_should_receive_and_save <= len(buffer.text):
                    buffer.switch_data(buffer.bytes_should_receive_and_save)
                    buffer.bytes_should_receive_and_save = 0
                    buffer.bytes_should_receive_and_ignore = 2
                else:
                    break
            elif buffer.bytes_should_receive_and_ignore:
                if buffer.bytes_should_receive_and_ignore <= len(buffer.text):
                    buffer.ignore_data(buffer.bytes_should_receive_and_ignore)
                    buffer.bytes_should_receive_and_ignore = 0
                else:
                    break

            else:
                pattern = ResponseParser.regex_end_chunk
                end_match = pattern.search(buffer.text)
                if end_match:
                    return buffer.message_verify()

                match = ResponseParser.regex_find_chunk.search(buffer.text)
                if match is None or match.groups()[0] == b'0':
                    break
                size = int(match.group('content_size'), 16)
                buffer.bytes_should_receive_and_save = size
                buffer.ignore_data(match.end() - match.start())

    def parse(self, buffer: 'Buffer') -> bytes | None:
        """
        General interface to work with parsing strategies
        :param buffer: A buffer which data should be parsed
        :type buffer: BaseBuffer
        :returns: Parsed and verified HTTP response or `NoneType` object
        :rtype: bytes or None
        """

        match self.value:
            case 'content_length':
                return self.parse_content_length(buffer)
            case 'chunked':
                return self.parse_chunked(buffer)


class BaseBuffer:

    @abstractmethod
    def __init__(self):
        ...

    @abstractmethod
    def add_data(self, text: bytes) -> tuple[bytes, bool] | Tuple[bytes, int] | Tuple[None, None]:
        ...

    def set_up(self) -> None:
        self.__init__()


class Buffer(BaseBuffer):
    """
    Implementing message receiving using ResponseParserStrategy which support
    receiving by content_length or chunked
    """

    def __init__(self) -> None:

        self.text = bytearray()
        self.__headers_done: bool = False
        self.body_receiving_strategy: ResponseParserStrategy | None = None
        self.content_length: int | None = None
        self.bytes_should_receive_and_save: int = 0
        self.bytes_should_receive_and_ignore: int = 0
        self.message_data: bytearray = bytearray()
        self.without_body_len: int | None = None
        self.verified: bool = False

    def switch_data(self, length: int) -> None:
        """
        Deletes from buffer's unparsed data and add to parsed ones
        :param length: Message length to delete from unpares data
        :returns: None
        """

        for byte in self.text[:length]:
            self.message_data.append(byte)
        self.text = self.text[length:]

    def message_verify(self) -> bytes:
        """
        Should be called whenever response messages seem full.

        :returns: None
        """

        msg = self.message_data

        self.message_data = bytearray()
        self.verified = True
        return msg

    def ignore_data(self, length: int) -> None:
        """
        Removes the elements from the buffer by the given length
        :param length: Bytes count to remove from the buffer's unparsed data
        :returns: None
        """

        self.text = self.text[length:]

    def headers_done(self) -> bool:
        """
        Checks if the text contains HTTP message data including full headers
        or full headers are not received yet.
        """

        if not self.__headers_done:
            is_done = ResponseParser.headers_done(self.text)
            if is_done:
                without_body_len = ResponseParser.get_without_body_length(self.text)
                self.without_body_len = without_body_len
                self.switch_data(without_body_len)
            self.__headers_done = is_done
        return self.__headers_done

    def find_strategy(self) -> None:
        """
        Finds and sets a strategy for getting a message, which can be chunked
        or by content_length
        :returns: None
        """

        content_length = ResponseParser.search_content_length(self.message_data)
        if content_length is not None:
            self.content_length = content_length
            self.body_receiving_strategy = ResponseParserStrategy.content_length
        else:
            self.body_receiving_strategy = ResponseParserStrategy.chunked
        log.trace(f"Strategy found: {self.body_receiving_strategy}")

    def fill_bytes(self, _bytes: bytes):
        """
        Adds given bytes into the buffer's unparsed data
        :param _bytes: Bytes to add to the buffer
        :returns: None
        """
        for byte in _bytes:
            self.text.append(byte)

    def add_data(self, text: bytes) -> Tuple[bytes, int] | Tuple[None, None]:
        """
        Called whenever new data is required to be added
        :param text: text to add
        :type text: bytes
        :returns: `Tuple[None, None]` if the message not verified else full body and without body len
        :rtype: Tuple[bytes, int] | Tuple[None, None]
        """

        self.fill_bytes(text)

        if self.headers_done():

            if not self.body_receiving_strategy:
                self.find_strategy()

            result = self.body_receiving_strategy.parse(self)  # type: ignore
            if result:
                return result, self.without_body_len
        return None, None


class StreamBuffer(BaseBuffer, ABC):
    """
    The buffer for stream responses.

    This class is meant to work with big response data. If it receives all response data at once, the program can crash
    because of ram overflow. Therefore, handling each chunk separately is also supported.
    """

    def __init__(self):
        self.buffer = Buffer()
        self.headers_skipped = False

    def add_data(self,
                 text: bytes) -> tuple[bytes, bool]:
        """
        Adds new bytes into the buffer and gets parsed result if possible, otherwise returns `None`
        """

        done = self.buffer.add_data(text)

        if self.buffer.verified:
            if self.headers_skipped:
                return done[0], True
            return done[0][self.buffer.without_body_len:], True

        if self.buffer.without_body_len:
            if not self.headers_skipped:  # if headers not received, receive and clean the bytearray
                self.headers_skipped = True

                # if transfer encoding was chunked, then with headers it can also receive some chunks
                # This code receive additional content which comes with `headers`
                body_received = self.buffer.message_data[self.buffer.without_body_len:]
                self.buffer.message_data = bytearray(b'')  # clear message_data
                return body_received, False
        msg = self.buffer.message_data
        self.buffer.message_data = bytearray(b'')  # clear message_data
        return msg, False
