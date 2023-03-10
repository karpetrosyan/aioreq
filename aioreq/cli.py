import argparse
import asyncio
from functools import wraps

import aioreq

parser = argparse.ArgumentParser()

parser.add_argument("url", type=str, help="HTTP resource URL")
parser.add_argument(
    "-X",
    "--method",
    type=str,
    choices=["GET", "POST", "PUT", "PATCH", "DELETE"],
    default="GET",
    help="HTTP method",
)
parser.add_argument(
    "-A", "--user-agent", type=str, default="aioreq", help="Set user-agent header"
)
parser.add_argument("-d", "--data", type=str, help="HTTP POST data")
parser.add_argument(
    "-H", "--headers", type=str, help="Send custom header(s) to server", nargs="*"
)
parser.add_argument("-o", "--output", type=str, help="Output file")
parser.add_argument(
    "-i", "--include", action="store_true", help="Include HTTP response headers"
)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="Show HTTP request headers"
)

args = parser.parse_args()


def preview(func=None, text=""):
    @wraps(func)
    def _inner(*args, **kwargs):
        nonlocal text
        local_text = text
        http_unit = args[0]

        space = 30
        if type(http_unit) == aioreq.Response:
            local_text = "RESPONSE " + local_text
        else:
            local_text = "REQUEST " + local_text
            space += 1
        print(local_text.center(space, "="))
        return func(*args, **kwargs)

    if func is None:

        def _inner_decorator(fnc):
            nonlocal func
            func = fnc
            return _inner

        return _inner_decorator
    return _inner


@preview(text="HEADERS")
def write_headers(http_unit, /):
    for key, value in http_unit.headers._headers.items():
        print(f"{key}: {value}")


@preview(text="OUTPUT")
def _print_output(output):
    print(output)


def write_output(output, response):
    output_file = args.output
    include = args.include

    if include:
        write_headers(response)

    if output_file:
        with open(output_file, "a+") as f:
            f.write(output)
    else:
        print(output)
    print()


def build_headers(parsed_headers):
    raw_headers = args.headers

    if args.data and ("content-type" not in parsed_headers):
        parsed_headers["content-type"] = "application/x-www-form-urlencoded"

    if not raw_headers:
        return parsed_headers

    for raw_header in raw_headers:
        key, value = raw_header.split(":")
        key = key.strip()
        value = value.strip()
        parsed_headers[key] = value
    return parsed_headers


async def _main():
    async with aioreq.Client(persistent_connections=False) as client:
        url = args.url
        data = args.data
        method = args.method

        parsed_headers = build_headers(client.headers)

        request = aioreq.Request(
            url=url, method=method, content=data, headers=parsed_headers
        )

        response = await client.send_request(request)

        if args.verbose:
            write_headers(request)

        output = response.content.decode()
        write_output(output=output, response=response)


def main():
    return asyncio.run(_main())
