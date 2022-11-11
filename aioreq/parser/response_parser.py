import re
import gzip
import logging

from ..settings import LOGGER_NAME
from ..protocol.headers import TransferEncoding
from ..protocol.headers import ContentEncoding
from ..protocol.encodings import Encodings

from ..utils import debug

log = logging.getLogger(LOGGER_NAME)


class ResponseParser:
    """
    Used to parse raw response becoming from TCP connection
    """
    # Default regex to parse full response
    regex = re.compile(
        (
            r'(?P<scheme_and_version>HTTP/[210].[210]) (?P<status_code>\d{3}) (?P<status_message>.*?)\r\n'
            r'(?P<headers>[\d\D]*?)\r\n'
            r'\r\n'
            r'(?P<body>[\d\D]*)'
        ).encode(),
    )

    regex_without_body = re.compile(
        (
            r'(?P<scheme_and_version>HTTP/[210].[210]) (?P<status_code>\d{3}) (?P<status_message>.*?)\r\n'
            r'(?P<headers>[\d\D]*?)\r\n'
            r'\r\n'
        ).encode()
    )

    # Regex to find content-length header if exists
    regex_content = (r'\r\nContent-length\s*:\s*(?P<length>\d*)\r\n',
                     re.IGNORECASE)

    regex_content_length = re.compile(
        regex_content[0].encode(),
        regex_content[1]
    )

    regex_without_body_length = re.compile(
        (r'(?P<scheme_and_version>.*) (?P<status_code>\d{3}) (?P<status_message>.*)\r\n'
         r'(?P<headers>(?:.*:? .*\r\n)*)'
         r'\r\n').encode()
    )

    regex_find_chunk = re.compile("^(?P<content_size>[0-9abcdefABCDEF]+)\r\n".encode())
    regex_end_chunks = (
        re.compile('^0\r\n\r\n'.encode()),
        re.compile('^\r\n\r\n'.encode())
    )

    @classmethod
    def parse_and_fill_headers(cls, binary_headers: bytes):
        headers = {}
        string_headers = binary_headers.decode()

        for line in string_headers.split('\r\n'):
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
        return headers

    @classmethod
    def decode_response_body(cls, response: 'Response') -> None:
        for parser, header in (
                (TransferEncoding, 'transfer-encoding'),
                (ContentEncoding, 'content-encoding')
        ):
            header_content = response.headers.get(header, None)
            if header_content:
                encodings = parser.parse(header_content)

                for encoding in encodings:
                    response.content = encoding.decompress(response.content)

        response.content = response.content[1:-1]

    @classmethod
    @debug.timer
    def parse(cls, response: bytes) -> 'Response':  # type: ignore
        """
        The main method for this class which parse response

        Parsing the raw response object and returning object type of
        Response which contains all becoming response data as his attributes
        :param response: raw response text
        :type response: bytes
        """

        from ..protocol.http import Response
        match = cls.regex.search(response)
        scheme_and_version, status, status_message, unparsed_headers, body = match.groups()  # type: ignore
        headers = cls.parse_and_fill_headers(unparsed_headers)
        status = int(status)
        status_message = status_message.decode()

        response = Response(
            status=status,
            status_message=status_message,
            headers=headers,
            content=body
        )

        cls.decode_response_body(response)
        return response

    @classmethod
    @debug.timer
    def body_len_parse(cls, text: bytes, without_body_len: int) -> 'Response':
        from ..protocol.http import Response

        withoutbody, body = text[:without_body_len], text[without_body_len:]

        match = cls.regex_without_body.search(withoutbody)
        scheme_and_version, status, status_message, unparsed_headers = match.groups()
        status = int(status)
        headers = cls.parse_and_fill_headers(unparsed_headers)

        response = Response(
            status=status,
            status_message=status_message,
            headers=headers,
            content=body
        )

        cls.decode_response_body(response)
        return response

    @classmethod
    @debug.timer
    def search_content_length(cls, text: bytes) -> int | None:
        """
        Search and returned content-length

        Search content-length header and return value if header exists
        using rexeg_content_length compiled regex
        :param text: text where content-length maybe exists
        :type text: bytes
        :returns: content_lenth | None
        :rtype: int or NoneType
        """

        match = cls.regex_content_length.search(text)
        if not match:
            return None
        content_length = match.group('length')
        return int(content_length)

    @classmethod
    @debug.timer
    def get_without_body_length(cls, text: bytes) -> int:
        """
        Get body less response

        Get index number from the text where body 
        part starting
        :param text: string where should be search
        :type text: bytes
        :returns: Index nuber where body part starts
        :rtype: int
        """

        match = cls.regex_without_body_length.match(text)
        assert match
        assert match.start() == 0, f"Got unexpected {match.start=}"
        return match.end() - match.start()

    @classmethod
    @debug.timer
    def headers_done(cls, text: bytes) -> bool:
        """
        Return true if text contains headers done text,
        which means HTTP message representing in string which
        contains an empty line
        """

        match = cls.regex_without_body_length.match(text)
        if match:
            assert match.start() == 0, f"Got unexpected {match.start=}"  # type: ignore
        return match is not None
