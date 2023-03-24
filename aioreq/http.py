import asyncio
import json
import logging
import sys
from abc import ABCMeta
from collections import defaultdict
from typing import Any
from typing import AsyncGenerator
from typing import DefaultDict
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

from aioreq.connection import StreamReader
from aioreq.connection import Transport
from aioreq.connection import resolve_domain
from aioreq.cookies import Cookies
from aioreq.generic import wrap_errors
from aioreq.parsers import ResponseParser
from aioreq.parsers import configure_json
from aioreq.parsers import configure_urlencoded
from aioreq.parsers import default_parser
from aioreq.settings import DEFAULT_TIMEOUT as REQUEST_TIMEOUT
from aioreq.settings import LOGGER_NAME
from aioreq.settings import REQUEST_REDIRECT_COUNT
from aioreq.settings import REQUEST_RETRY_COUNT
from aioreq.urls import Uri3986
from aioreq.urls import parse_url

from .headers import ContentType
from .headers import Headers
from .middlewares import MiddleWare
from .middlewares import RedirectMiddleWare
from .middlewares import RetryMiddleWare
from .middlewares import default_middlewares
from .settings import DEFAULT_HEADERS

if (sys.version_info.major, sys.version_info.minor) > (3, 9):
    from typing import TypeAlias  # type: ignore[attr-defined]
else:
    from typing_extensions import TypeAlias  # type: ignore[attr-defined]

URLENCODED: TypeAlias = Union[Dict[str, str], Iterable[Tuple[str, str]]]
CONTENT: TypeAlias = Union[str, bytearray, bytes]
BR = TypeVar("BR", bound="BaseRequest")
log = logging.getLogger(LOGGER_NAME)


class BaseRequest:
    def __init__(
        self,
        url: Union[Uri3986, str],
        *,
        headers: Union[Headers, Dict[str, str], None] = None,
        method: str = "GET",
        content: Any = "",
        params: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ) -> None:
        if isinstance(url, Uri3986):
            self._url = url
        else:
            self._url = parse_url(url)

        if self._url.query and params:
            raise ValueError(
                (
                    "Request incorporates the query parameter into"
                    " the URL or as an argument, but not both."
                )
            )
        self._url.query = params or self._url.query

        self.auth = auth
        self.headers = Headers(headers)
        self.timeout = timeout
        self.params = self._url.query
        self.method = method
        self.content = content
        self._raw_request: Optional[bytes] = None
        self.check_hostname = check_hostname
        self.verify_mode = verify_mode
        self.keylog_filename = keylog_filename
        self.stream = stream

    @property
    def url(self) -> Union[Uri3986]:
        return self._url

    @url.setter
    def url(self, value) -> None:
        self._url = parse_url(value)
        self.params = self._url.query

    def get_raw_request(self) -> bytes:
        if self._raw_request:
            return self._raw_request

        message = default_parser(self)
        enc_message = message.encode("utf-8")
        self._raw_request = enc_message
        return enc_message

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.method} {self.url.get_domain()}>"

    def __getattribute__(self, item):
        self._raw_request = None
        return super().__getattribute__(item)


class BaseResponse:
    ...


class Request(BaseRequest):
    """HTTP Request with no additional configurations."""

    parse_config = None

    def __init__(
        self,
        url: Union[Uri3986, str],
        *,
        headers: Union[Headers, Dict[str, str], None] = None,
        method: str = "GET",
        content: Optional[CONTENT] = None,
        params: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ):
        super().__init__(
            url=url,
            headers=headers,
            method=method,
            content=content,
            params=params,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )


class JsonRequest(BaseRequest):
    """JSON Request that dumps the context using a json encoder."""

    parse_config = configure_json

    def __init__(
        self,
        url: Union[Uri3986, str],
        *,
        headers: Union[Headers, Dict[str, str], None] = None,
        method: str = "GET",
        content: Optional[Dict] = None,
        params: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ):
        super().__init__(
            url=url,
            headers=headers,
            method=method,
            content=content,
            params=params,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )


class UrlEncodedRequest(BaseRequest):
    parse_config = configure_urlencoded

    def __init__(
        self,
        url: Union[Uri3986, str],
        *,
        headers: Union[Headers, Dict[str, str], None] = None,
        method: str = "GET",
        content: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        params: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ):
        super().__init__(
            url=url,
            headers=headers,
            method=method,
            content=content,
            params=params,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )


class Response(BaseResponse):
    """This object represents a simple HTTP response."""

    def __init__(
        self,
        status: int,
        status_message: str,
        headers: Union[Headers, Dict[str, str]],
        content: Optional[bytes],
        request: Union[Request, None] = None,
        stream: Optional[StreamReader] = None,
    ):
        self.status = status
        self.status_message = status_message
        self.headers = Headers(headers)
        self.content = content
        self.request = request
        self.redirects = None
        self.stream = stream

    def _check_stream(self) -> None:
        if self.content is None and self.stream:
            raise Exception(
                "Attempting to read a stream "
                "response without actually reading "
                "it. use read stream() to accomplish this."
            )

    @property
    def text(self, encoding: Optional[str] = None) -> str:
        self._check_stream()

        if not encoding:
            content_type = ContentType.parse(self.headers.get("Content-Type"))
            encoding = content_type.charset or "utf-8"
        return self.content.decode(encoding)  # type: ignore[union-attr]

    @property
    def json(self, encoding: Optional[str] = None) -> dict:
        self._check_stream()

        if not encoding:
            content_type = ContentType.parse(self.headers.get("Content-Type"))
            encoding = content_type.charset or "utf-8"
        return json.loads(self.content.decode(encoding))  # type: ignore[union-attr]

    async def iter_bytes(self, max_read: int) -> AsyncGenerator[bytes, None]:
        assert self.stream
        async for chunk in self.stream.read_by_chunks(max_read=max_read):
            yield chunk

    async def read_stream(self) -> bytes:
        content = b""
        assert self.stream
        async for chunk in self.stream.read_by_chunks(max_read=1024):
            content += chunk
        self.content = content
        return content

    def __eq__(self, _value) -> bool:
        if type(self) != type(_value):
            raise TypeError(
                f"Can't compare `{type(self).__name__}` with `{type(_value).__name__}`"
            )
        return (
            self.status == _value.status
            and self.status_message == _value.status_message
            and self.headers == _value.headers
            and self.content == _value.content
            and self.request == _value.request
        )

    def __repr__(self) -> str:
        return f"<Response {self.status} {self.status_message}>"


class BaseClient(metaclass=ABCMeta):
    """The base client for all HTTP clients, implementing all core methods."""

    def __init__(
        self,
        headers: Union[Dict[str, str], Headers, None] = None,
        persistent_connections: bool = False,
        redirect_count: int = REQUEST_REDIRECT_COUNT,
        retry_count: int = REQUEST_RETRY_COUNT,
        timeout: Union[int, float] = REQUEST_TIMEOUT,
        auth: Optional[Tuple[str, str]] = None,
        middlewares: Optional[Tuple[Union[str, Type[MiddleWare]], ...]] = None,
        cookies: Optional[Cookies] = None,
    ):
        headers = Headers(initial_headers=DEFAULT_HEADERS) | Headers(
            initial_headers=headers
        )

        if isinstance(cookies, Cookies):
            self.cookies = cookies
        elif cookies is None:
            self.cookies = Cookies()

        RedirectMiddleWare.redirect_count = redirect_count
        RetryMiddleWare.retry_count = retry_count
        if middlewares is None:
            self.middlewares = MiddleWare.build(default_middlewares)
        else:
            self.middlewares = MiddleWare.build(middlewares)

        self.timeout = timeout
        self.redirect = redirect_count
        self.retry = retry_count
        self.auth = auth
        self.connection_mapper: DefaultDict[str, list] = defaultdict(list)
        self.headers = headers
        self.transports: List[Transport] = []
        self.persistent_connections = persistent_connections

    def _build_request(
        self,
        url: str,
        method: str,
        content: CONTENT = "",
        json: Optional[Dict] = None,
        urlencoded: Optional[URLENCODED] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Union[None, Dict[str, str], Headers] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ) -> BaseRequest:
        """Creates one of the "Request" instances based on attributes."""

        headers = Headers(initial_headers=headers)
        content_found = False
        mixed_content: Union[Optional[URLENCODED], Optional[CONTENT], Optional[Dict]]
        request_class: Type[BaseRequest]

        for cnt in (content, json, urlencoded):
            if cnt:
                if content_found:
                    msg = (
                        "You can only use one of those parameters"
                        " (`content`, `json`, `urlencoded`)"
                    )
                    raise ValueError(msg)
                content_found = True

        if json:
            request_class = JsonRequest
            mixed_content = json
        elif urlencoded:
            request_class = UrlEncodedRequest
            mixed_content = urlencoded
        else:
            request_class = Request
            mixed_content = content
        request = request_class(
            url=url,
            method=method,
            headers=self.headers | headers,
            params=params,
            content=mixed_content,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )
        return request

    async def __aenter__(self):
        return self

    def __str__(self):
        return (
            f"{self.headers}"
            f"\nself.persistent_connections={self.persistent_connections}"
            f"\nself.retry={self.retry} | self.redirect={self.redirect}"
        )

    async def __aexit__(self, *args, **kwargs):
        """Closes all open connections for this Client."""

        tasks = []
        for transport in self.transports:
            assert transport.writer
            transport.writer.close()
            tasks.append(transport.writer.wait_closed())
        await asyncio.gather(*tasks)


class Client(BaseClient):
    methods = ("GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH")

    async def send_request_directly(self, request: Request) -> Response:
        """The only method that sends HTTP
        requests to servers via `Transport` instances."""

        transport = await self._get_connection(
            url=request.url,
            check_hostname=request.check_hostname,
            verify_mode=request.verify_mode,
            keylog_filename=request.keylog_filename,
        )

        coro = transport.send_http_request(
            request.get_raw_request(), stream=request.stream
        )
        with wrap_errors():
            status_line, header_line, content = await coro

        resp = ResponseParser.parse(status_line, header_line, content)
        resp.request = request
        return resp

    async def _send_request_via_middleware(self, request: BaseRequest) -> Response:
        """Sends Request instances to the middlewares chain.l"""

        response = await self.middlewares.process(request, client=self)
        return response

    async def _get_connection(
        self,
        url: Uri3986,
        verify_mode: bool,
        check_hostname: bool,
        keylog_filename: Optional[str],
    ) -> Transport:
        """If a connection to the same IP and port was not found in the
        "connection_mapper", this method returns the newly opened connection;
         otherwise, it returns the previously opened one."""

        transport = None
        domain = url.get_domain()
        if self.persistent_connections:
            log.trace(  # type: ignore
                f"{self.connection_mapper} " "searching into mapped connections"
            )

            for transport in self.connection_mapper[domain]:
                if not transport.used:
                    if transport.is_closing():
                        del self.connection_mapper[domain]
                    else:
                        break
            else:
                transport = None

        if not transport:
            ip, port = await resolve_domain(url)

            transport = Transport()
            connection_coroutine = transport.make_connection(
                ip,
                port,
                ssl=url.scheme == "https",
                server_hostname=domain,
                check_hostname=check_hostname,
                verify_mode=verify_mode,
                keylog_filename=keylog_filename,
            )

            await connection_coroutine
            self.transports.append(transport)

            if self.persistent_connections:
                self.connection_mapper[domain].append(transport)
        else:
            log.debug("Using already opened connection")
        return transport

    async def _send_request(
        self,
        url: str,
        method: str,
        content: CONTENT = "",
        json: Optional[Dict] = None,
        urlencoded: Optional[URLENCODED] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Union[None, Dict[str, str], Headers] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ) -> Response:
        """
        Builds and sends newly created requests to middlewares.
        Clients' GET, POST, PATCH, and other methods
        use this method by default to send requests.
        """
        request = self._build_request(
            url=url,
            method=method,
            content=content,
            json=json,
            urlencoded=urlencoded,
            params=params,
            headers=headers,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )
        return await self._send_request_via_middleware(request)

    async def send_request(self, request: Request) -> Response:
        """Send the Request instance to the middlewares."""
        return await self._send_request_via_middleware(
            request=request,
        )

    async def get(
        self,
        url: str,
        content: CONTENT = "",
        json: Optional[Dict] = None,
        urlencoded: Optional[URLENCODED] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="GET",
            content=content,
            json=json,
            urlencoded=urlencoded,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )

    async def post(
        self,
        url: str,
        content: CONTENT = "",
        json: Optional[Dict] = None,
        urlencoded: Optional[URLENCODED] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="POST",
            content=content,
            json=json,
            urlencoded=urlencoded,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )

    async def put(
        self,
        url: str,
        content: CONTENT = "",
        json: Optional[Dict] = None,
        urlencoded: Optional[URLENCODED] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="PUT",
            content=content,
            json=json,
            urlencoded=urlencoded,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )

    async def delete(
        self,
        url: str,
        content: CONTENT = "",
        json: Optional[Dict] = None,
        urlencoded: Optional[URLENCODED] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="DELETE",
            content=content,
            json=json,
            urlencoded=urlencoded,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )

    async def options(
        self,
        url: str,
        content: CONTENT = "",
        json: Optional[Dict] = None,
        urlencoded: Optional[URLENCODED] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="OPTIONS",
            content=content,
            json=json,
            urlencoded=urlencoded,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )

    async def head(
        self,
        url: str,
        content: CONTENT = "",
        json: Optional[Dict] = None,
        urlencoded: Optional[URLENCODED] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="HEAD",
            content=content,
            json=json,
            urlencoded=urlencoded,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )

    async def patch(
        self,
        url: str,
        content: CONTENT = "",
        json: Optional[Dict] = None,
        urlencoded: Optional[URLENCODED] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="PATCH",
            content=content,
            json=json,
            urlencoded=urlencoded,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )

    async def link(
        self,
        url: str,
        content: CONTENT = "",
        json: Optional[Dict] = None,
        urlencoded: Optional[URLENCODED] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
        stream: bool = False,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="LINK",
            content=content,
            json=json,
            urlencoded=urlencoded,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
            stream=stream,
        )
