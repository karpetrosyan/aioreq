import json as _json
import logging
import re
from datetime import datetime

from aioreq.settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)


def sum_path_parameters(parameters):
    return "&".join([f"{key}={value}" for key, value in parameters.items()])


def default_parser(request):
    url = request.url
    path = url.path or "/"
    query = url.query or ""
    domain = url.get_domain()

    if query:
        query = "?" + sum_path_parameters(query)

    if type(request.content) in (bytes, bytearray):
        request.content = request.content.decode()

    if request.content:
        request.headers["Content-Length"] = len(request.content)

    if request.parse_config:
        request.parse_config()

    path += query
    message = (
            "\r\n".join(
                (
                    f"{request.method} {path} HTTP/1.1",
                    f"host:  {domain}",
                    request.headers.get_parsed(),
                )
            )
            + "\r\n"
    )

    message += request.content or ""
    return message


def configure_json(request):
    payload = request.content

    if payload:
        if isinstance(payload, str):
            payload = _json.loads(payload)  # validate json format
        payload = _json.dumps(payload)

        request.headers["content-type"] = "application/json"
        request.headers["Content-Length"] = len(payload)
        request.content = payload


class ResponseParser:
    # Regex to find content-length header if exists
    regex_content = (r"content-length\s*:\s*(?P<length>\d*)\r\n", re.IGNORECASE)
    regex_content_length = re.compile(regex_content[0], regex_content[1])

    @classmethod
    def parse_and_fill_headers(cls, raw_headers):
        from aioreq.headers import Headers

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
        from aioreq.http import Response

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

    @classmethod
    def search_transfer_encoding(cls, text):
        return 'transfer-encoding' in text.lower()

class DateParser6265:
    non_delimiter_ranges = (
        (0x00, 0x08),
        (0x0A, 0x1F),
        (48, 58),
        (97, 123),
        (0x7F, 0xFF),
        (65, 91),
    )
    non_delimiter = {
                        ":",
                    } | set(
        chr(i) for start, end in non_delimiter_ranges for i in range(start, end))

    hms_time_regex = re.compile(r"(\d{1,2}:){2}\d{1,2}")
    year_regex = re.compile(r"\d{2,4}")
    day_of_month_regex = re.compile(r"\d{1,2}")
    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    def validate(
            self,
            year_value,
            minute_value,
            second_value,
            day_of_month_value,
            month_value,
            hour_value,
            found_month,
            found_year,
            found_time,
    ):
        if 70 <= year_value <= 99:
            year_value += 1900
        if 0 <= year_value <= 69:
            year_value += 2000

        if (
                not (all((day_of_month_value, found_month, found_year, found_time)))
                and (1 <= day_of_month_value <= 31)
                and (year_value < 1601)
                and (hour_value > 23)
                and (minute_value > 59)
                and (second_value > 59)
        ):
            raise ValueError("Invalid date")
        return datetime(
            year=year_value,
            month=month_value,
            day=day_of_month_value,
            hour=hour_value,
            minute=minute_value,
            second=second_value,
        )

    def parse(self, date):
        date_tokens = []
        start = None

        for ind, char in enumerate(date):
            if char not in self.non_delimiter:
                if start is not None:
                    date_tokens.append(date[start:ind])
                    start = None
            else:
                if start is None:
                    start = ind
        if start is not None:
            date_tokens.append(date[start:])

        found_time = None
        found_day_of_month = None
        found_month = None
        found_year = None

        hour_value = None
        minute_value = None
        second_value = None
        day_of_month_value = None
        month_value = None
        year_value = None

        for token in date_tokens:
            if not found_time and self.hms_time_regex.match(token):
                found_time = True
                hour_value, minute_value, second_value = token.split(":")
                hour_value = int(hour_value)
                minute_value = int(minute_value)
                second_value = int(second_value)

            elif not found_month and token.lower() in self.month_map:
                found_month = True
                month_value = int(self.month_map[token.lower()])

            elif not found_day_of_month and self.day_of_month_regex.match(token):
                found_day_of_month = True
                day_of_month_value = int(token)

            elif not found_year and self.year_regex.match(token):
                found_year = True
                year_value = int(token)

        try:
            return self.validate(
                year_value=year_value,
                month_value=month_value,
                second_value=second_value,
                minute_value=minute_value,
                hour_value=hour_value,
                day_of_month_value=day_of_month_value,
                found_month=found_month,
                found_year=found_year,
                found_time=found_time,
            )
        except ValueError:
            return None
