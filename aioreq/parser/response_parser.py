import re
import logging

from ..settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)

class ResponseParser:
    regex = re.compile(
        r'(?P<scheme_and_version>.*) (?P<status_code>\d{3}) (?P<status_message>.*)\r\n'
        r'(?P<headers>(?:.*:? .*\r\n)*)'
        r'\r\n'
        r'(?P<body>[\d\D]*)'
        )

    regex_content_length = re.compile(
            r'[\s\S]*content-length\s*:\s*(?P<length>\d*)\r\n',
            re.IGNORECASE
            )

    regex_without_body_length = re.compile(
        r'(?P<scheme_and_version>.*) (?P<status_code>\d{3}) (?P<status_message>.*)\r\n'
        r'(?P<headers>(?:.*:? .*\r\n)*)'
        r'\r\n'
            )

    @classmethod
    def parse(cls, response) -> 'Response':
        from ..protocol.http import Response
        match = cls.regex.search(response)
        scheme_and_version, status, status_message, unparsed_headers, body = match.groups()
        headers = {}
        log.debug(f"Got response {unparsed_headers=}")
        for line in unparsed_headers.split('\r\n')[:-1]:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()

        return Response(
                scheme_and_version = scheme_and_version,
                status = status,
                status_message = status_message,
                headers = headers,
                body = body
                )

    @classmethod
    def search_content_length(cls, text):
        match = cls.regex_content_length.search(text)
        if not match:
            return False
        content_length = match.group('length')
        return int(content_length)

    @classmethod
    def get_without_body_length(cls, text):
        match = cls.regex_without_body_length.match(text)
        assert match
        assert match.start() == 0, f"Got unexpected {match.start=}"
        return match.end() - match.start()
        

