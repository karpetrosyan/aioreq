import re
import logging

from ..settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)

class BaseResponseParser:
    """
    Change me
    """
    ...

class ResponseParser:
    """
    Used to parse raw response becoming from TCP connection
    """
    # Default regex to parse full response
    regex = re.compile(
        r'(?P<scheme_and_version>.*) (?P<status_code>\d{3}) (?P<status_message>.*)\r\n'
        r'(?P<headers>(?:.*:? .*\r\n)*)'
        r'\r\n'
        r'(?P<body>[\d\D]*)'
        )
    # Regex to find content-length if exists
    regex_content_length = re.compile(
            r'[\s\S]*content-length\s*:\s*(?P<length>\d*)\r\n',
            re.IGNORECASE
            )

    regex_without_body_length = re.compile(
        r'(?P<scheme_and_version>.*) (?P<status_code>\d{3}) (?P<status_message>.*)\r\n'
        r'(?P<headers>(?:.*:? .*\r\n)*)'
        r'\r\n'
            )

    regex_find_chunk = re.compile("^(?P<content_size>\d+)\r\n")
    regex_end_chunks = (
            re.compile('0\r\n\r\n'), 
            re.compile('\r\n\r\n')
                        )

    @classmethod
    def parse(cls, response: str) -> 'Response':
        """
        The main method for this class which parse response

        Parsing the raw response object and returning object type of
        Response which contains all becoming response data as his attributes

        :param response: raw response text
        :type response: str
        """

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
    def search_content_length(cls, text: str) -> int | None:
        """
        Search and returned content-length

        Search content-length header and return value if header exists
        using rexeg_content_length compiled regex

        :param text: text where content-length maybe exists
        :type text: str
        :returns: content_lenth | None
        :rtype: int or NoneType
        """

        match = cls.regex_content_length.search(text)
        if not match:
            return None
        content_length = match.group('length')
        return int(content_length)

    @classmethod
    def get_without_body_length(cls, text: str) -> int:
        """
        Get body less response

        Get index number from the text where body 
        part starting

        :param text: string where should be search
        :type text: str
        :returns: Index nuber where body part starts
        :rtype: int
        """

        match = cls.regex_without_body_length.match(text)
        assert match
        assert match.start() == 0, f"Got unexpected {match.start=}"
        return match.end() - match.start()

    @classmethod
    def headers_done(cls, text:str) -> bool:
        """
        Return true if text contains headers done text,
        which means HTTP message representing in string which
        contains an empty line
        """

        match = cls.regex_without_body_length.match(text)
        assert match.start() == 0, f"Got unexpected {match.start=}"
        return match is not None
        

