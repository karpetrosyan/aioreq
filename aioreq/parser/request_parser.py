import json as _json

from typing import Iterable


class BaseRequestParser:
    """
    For parsing Request object to raw data which can be sent
    via socket
    """

    # @abstractmethod
    @classmethod
    def parse(cls, request: "Request") -> str:
        ...  # type: ignore

    @classmethod
    def sum_path_parameters(cls, parameters: Iterable[Iterable[str]]):
        return "&".join([f"{key}={value}" for key, value in parameters])


class RequestParser(BaseRequestParser):
    @classmethod
    def parse(cls, request: "Request") -> str:  # type: ignore
        """
        Parsing object type of request to string representing HTTP message

        :returns: raw http request text
        :rtype: str
        """

        if isinstance(request.content, bytearray) or isinstance(request.content, bytes):
            request.content = request.content.decode()

        if request.path_parameters:
            request.path += "?" + cls.sum_path_parameters(request.path_parameters)

        if request.content:
            request.headers["Content-Length"] = len(request.content)

        message = (
            "\r\n".join(
                (
                    f"{request.method} {request.path} {request.scheme_and_version}",
                    f'host:  {request.host.split("://", 1)[1]}',
                    request.headers.get_parsed(),
                )
            )
            + "\r\n"
        )

        message += request.content or ""
        return message


class JsonRequestParser(BaseRequestParser):
    @classmethod
    def parse(cls, request: "Request") -> str:  # type: ignore
        """
        Parsing object type of request to string representing HTTP message

        :returns: raw http request text
        :rtype: str
        """

        if isinstance(request.content, bytearray) or isinstance(request.content, bytes):
            request.content = request.content.decode()

        if request.path_parameters:
            request.path += "?" + cls.sum_path_parameters(request.path_parameters)

        if request.content:
            request.content = _json.dumps(request.content)[1:-1]
            request.headers["Content-Type"] = "application/json"
            request.headers["Content-Length"] = len(request.content)

        message = (
            "\r\n".join(
                (
                    f"{request.method} {request.path} {request.scheme_and_version}",
                    f'host:  {request.host.split("://", 1)[1]}',
                    *(f"{key}:  {value}" for key, value in request.headers.items()),
                )
            )
            + "\r\n\r\n"
        )

        message += request.content or ""

        return message
