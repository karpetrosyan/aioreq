import re

from ..prorocol.messages import Response

class ResponseParser:
    regex = re.compile(
        r'(?P<scheme_and_version>.*) (?P<status_code>\d{3}) (?P<status_message>.*)\r\n'
        r'(?P<headers>(?:.*:? .*\r\n)*)'
        r'\r\n'
        r'(?P<body>[\d\D]*)\r\n\r\n'
        )

    @classmethod
    def parse(cls, response) -> Respone:
        match = cls.regex.search(response)
        scheme_and_version, status, status_message, unparsed_headers, body = match.groups()
        headers = {}

        for line in unparsed_headers.split('\r\n')[:-1]:
            key, value = line.split(':')
            headers[key.strip()] = value.strip()

        return Response(
                scheme_and_version = scheme_and_version,
                status = status,
                status_message = status_message,
                headers = headers,
                body = body
                )


resp = (f"HTTP/1.1 200 OK\r\n"
        f'ASDasdf: dasf\r\n'
        f'ASDasd: dasf\r\n'
        f'ASDa: dasf\r\n'
        f'ASD: sf\r\n'
        f'\r\n'
        f'this is body message\nasdfasd\nasdfasdf\r\n\r\n')
match = (ResponseParser.parse(resp))
