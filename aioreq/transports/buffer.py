import logging

from enum import Enum
from ..settings import LOGGER_NAME
from ..parser.response_parser import ResponseParser

from typing import Tuple

log = logging.getLogger(LOGGER_NAME)


class ResponseParserStrategy(Enum):
    """
    Enumeration which implements Strategy design pattern, used to
    choose a way of parsing response
    """
    chunked = 'chunked'
    content_length = 'content_length'

    @staticmethod
    def parse_content_length(buffer: 'Buffer') -> bytes | None:
        """
        Parse incoming PendingMessage object which receiving data which body length
        specified by Content-Length header.

        RFC[2616] 14.13 Content-Length:
            The Content-Lenght entity-header field indicates the size of the entity-body,
            in decimal number of OCTETs, sent to the recipent or, in the case of the HEAD method,
            the size of the entity-body that would have been sent had the request been a GET
        :param buffer: Buffer instance representing message receiving
        :return: None or the verified string which seems like an HTTP message
        """

        if len(buffer.text) >= buffer.content_length:
            buffer.switch_data(buffer.content_length)
            return buffer.message_verify()
        return None

    @staticmethod
    def parse_chunked(buffer: 'Buffer') -> None | bytes:
        """
        Parse incoming PendingMessage object which receiving data which body length
        specified by Transfer-Encoding : chunked.

        RFC[2616] 3.6.1 Chunked Transfer Coding:
            The chunked encoding modifies the body of a message in order to transfer it as a series of
            chunkd, each with its own size indicator, followed by an OPTIONAL trailer containing entity-header
            fields. This allows dynamically produced content to be transferred along with the information
            necessary for the recipient to verify that it has received the full message
        :param buffer: aioreq.transports.buffer.Buffer object
        :type buffer: Buffer
        :return: None or the verified string which seems like an HTTP message 
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
        :param buffer: aioreq.transports.buffer.Buffer object
        :type buffer: Buffer

        :returns: Parsed and verifyed http response or NoneType object
        :rtype: bytes or None
        """

        match self.value:
            case 'content_length':
                return self.parse_content_length(buffer)
            case 'chunked':
                return self.parse_chunked(buffer)


class BaseBuffer:
    ...


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
        Delete from unparsed data and add to parsed ones
        :param length: Message length to delete from unpares data
        :return: None
        """

        for byte in self.text[:length]:
            self.message_data.append(byte)
        self.text = self.text[length:]

    def message_verify(self) -> bytes:
        """
        If message seems like full, call this method to return and clean the
        self.message_data

        :returns: None
        """

        msg = self.message_data

        self.message_data = bytearray()
        self.verified = True
        return msg

    def ignore_data(self, length: int) -> None:
        """
        Just delete text length of {length} from unparsed data
        :param length: Length message which should be ignored (deleted)
        :returns: None
        """

        self.text = self.text[length:]

    def headers_done(self) -> bool:
        """
        Check if text contains HTTP message data included full headers
        or there is headers coming now
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
        Find and set strategy for getting message, it can be chunked receiving or
        with content_length

        :returns: None
        """

        content_length = ResponseParser.search_content_length(self.message_data)
        if content_length is not None:
            self.content_length = content_length
            self.body_receiving_strategy = ResponseParserStrategy.content_length
        else:
            self.body_receiving_strategy = ResponseParserStrategy.chunked
        log.debug(f"Strategy found: {self.body_receiving_strategy}")

    def fill_bytes(self, _bytes: bytes):
        for byte in _bytes:
            self.text.append(byte)

    def add_data(self, text: bytes) -> Tuple[bytes, int] | Tuple[None, None]:
        """
        Calls whenever new data required to be added
        :param text: Text to add
        :ptype text: str

        :returns: None if message not verified else verified message
        """

        self.fill_bytes(text)

        if self.headers_done():

            if not self.body_receiving_strategy:
                self.find_strategy()

            result = self.body_receiving_strategy.parse(self)  # type: ignore
            if result:
                return result, self.without_body_len
        return None, None


class StreamBuffer(BaseBuffer):
    """
    A buffer for stream responses.

    This class is meant to work with large response data. If receiving all response data at once, it can crash our
    program because of ram overflow, so handling each chunk separately is also supported.
    """

    def __init__(self):
        self.buffer = Buffer()
        self.headers_skipped = False

    def add_data(self,
                 text: bytes) -> tuple[bytes, bool] | bytes:
        """
        :returns: None if
        """
        print('given', text)
        done = self.buffer.add_data(text)

        if self.buffer.verified:
            if self.headers_skipped:
                return done[0], True
            return done[0][self.buffer.without_body_len:], True

        if self.buffer.without_body_len:
            if not self.headers_skipped:  # if headers not received, receive and clean the bytearray
                self.headers_skipped = True
                body_received = self.buffer.message_data[self.buffer.without_body_len:]
                self.buffer.message_data = bytearray(b'')
                return body_received, False
        msg = self.buffer.message_data
        self.buffer.message_data = bytearray(b'')
        print(msg)
        return msg, False
