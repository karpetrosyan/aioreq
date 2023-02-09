import logging
import re

from ..settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)


class ResponseParser:
    # Regex to find content-length header if exists
    regex_content = (r"content-length\s*:\s*(?P<length>\d*)\r\n", re.IGNORECASE)
    regex_content_length = re.compile(regex_content[0], regex_content[1])

    @classmethod
    def parse_and_fill_headers(cls, raw_headers):
        from .. import Headers

        headers = Headers()
        raw_headers = raw_headers.strip("\r\n")
        for line in raw_headers.split("\r\n"):
            key, value = line.split(":", 1)
            headers[key] = value.strip()
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
    def search_content_length(cls, text):
        match = cls.regex_content_length.search(text)
        if not match:
            return None
        content_length = match.group("length")
        return int(content_length)
