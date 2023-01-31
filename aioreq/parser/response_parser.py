import logging
import re
from typing import Union

from ..protocol.headers import ContentEncoding
from ..protocol.headers import TransferEncoding
from ..settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)


class ResponseParser:
    """
    Used to parse raw response becoming from TCP connection
    """

    # Default regex to parse full response

    # Regex to find content-length header if exists
    regex_content = (r"\r\nContent-length\s*:\s*(?P<length>\d*)\r\n", re.IGNORECASE)

    regex_content_length = re.compile(regex_content[0], regex_content[1])

    @classmethod
    def parse_and_fill_headers(cls, raw_headers):
        from .. import Headers

        headers = Headers()
        raw_headers = raw_headers.strip("\r\n")
        for line in raw_headers.split("\r\n"):
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
        return headers

    @classmethod
    def parse_status_line(cls, raw_status_line):
        scheme, status, status_message = raw_status_line.split(maxsplit=2)
        return scheme, int(status), status_message

    @classmethod
    def parse(cls, status_line, header_line, content):
        from ..protocol.http import Response

        scheme, status, status_message = cls.parse_status_line(status_line)
        status_message = status_message[:-2]
        status = int(status)
        headers = cls.parse_and_fill_headers(header_line)

        response = Response(
            status=status,
            status_message=status_message,
            headers=headers,
            content=content,
        )

        return response

    @classmethod
    def search_content_length(cls, text: bytes) -> Union[int, None]:
        """
        Search and returned content-length

        Search content-length header and return value if header exists
        using regex_content_length compiled regex
        :param text: text where content-length maybe exists
        :type text: bytes
        :returns: content_lenth | None
        :rtype: int or NoneType
        """

        match = cls.regex_content_length.search(text)
        if not match:
            return None
        content_length = match.group("length")
        return int(content_length)
