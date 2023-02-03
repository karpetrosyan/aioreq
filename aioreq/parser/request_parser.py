import json as _json


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
