import asyncio
import logging
from abc import ABCMeta
from collections import defaultdict
from typing import (
    AsyncGenerator,
    AsyncIterator,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from rfcparser.object_abstractions import Uri3986

from aioreq.protocol.connection import Transport, resolve_domain

from ..parser.request_parser import configure_json, default_parser
from ..parser.response_parser import ResponseParser
from ..parser.url_parser import parse_url
from ..settings import DEFAULT_TIMEOUT as REQUEST_TIMEOUT
from ..settings import LOGGER_NAME, REQUEST_REDIRECT_COUNT, REQUEST_RETRY_COUNT
from ..utils.generic import wrap_errors
from .cookies import Cookies
from .headers import Headers
from .middlewares import (
    MiddleWare,
    RedirectMiddleWare,
    RetryMiddleWare,
    default_middlewares,
)

log = logging.getLogger(LOGGER_NAME)

TRESP = TypeVar("TRESP", bound="Response")


class BaseRequest:
    def __init__(
        self,
        url: Union[Uri3986, str],
        *,
        headers: Union[Headers, Dict[str, str], None] = None,
        method: str = "GET",
        content: Union[str, bytearray, bytes] = "",
        params: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Union[int, float, None] = None,
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

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
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
    parse_config = None


class JsonRequest(BaseRequest):
    parse_config = configure_json


class Response(BaseResponse):
    def __init__(
        self,
        status: int,
        status_message: str,
        headers: Union[Headers, Dict[str, str]],
        content: bytes,
        request: Union[Request, None] = None,
    ):
        self.status = status
        self.status_message = status_message
        self.headers = Headers(headers)
        self.content = content
        self.request = request
        self.redirects = None

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


class StreamResponse(BaseResponse):
    def __init__(
        self,
        status: int,
        status_message: str,
        headers: Headers,
        content: AsyncGenerator,
        request: Request,
    ):
        self.status = status
        self.status_message = status_message
        self.headers = headers
        self.content = content
        self.request = request


class BaseClient(metaclass=ABCMeta):
    def __init__(
        self,
        headers: Union[Dict[str, str], Headers, None] = None,
        persistent_connections: bool = False,
        redirect_count: int = REQUEST_REDIRECT_COUNT,
        retry_count: int = REQUEST_RETRY_COUNT,
        timeout: Union[int, float] = REQUEST_TIMEOUT,
        auth: Optional[Tuple[str, str]] = None,
        middlewares: Optional[Tuple[Union[str, Type[MiddleWare]], ...]] = None,
        cookies: Optional[Union[Cookies, Dict]] = None,
    ):
        headers = Headers(initial_headers=headers)

        if isinstance(cookies, Cookies):
            self.cookies = cookies
        elif isinstance(cookies, dict):
            self.cookies = Cookies(cookies)
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
        self.connection_mapper: defaultdict[str, list] = defaultdict(list)
        self.headers = headers
        self.transports: List[Transport] = []
        self.persistent_connections = persistent_connections

    async def _get_connection(self, url):
        transport = None
        domain = url.get_domain()
        if self.persistent_connections:
            log.trace(f"{self.connection_mapper} searching into mapped connections")

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
                **{"ssl": True, "server_hostname": domain}
                if url.scheme == "https"
                else {**{"ssl": False, "server_hostname": None}},
            )
            await connection_coroutine
            self.transports.append(transport)

            if self.persistent_connections:
                self.connection_mapper[domain].append(transport)
        else:
            log.debug("Using already opened connection")
        return transport

    async def __aenter__(self):
        return self

    def __str__(self):
        return (
            f"{self.headers}"
            f"\nself.persistent_connections={self.persistent_connections}"
            f"\nself.retry={self.retry} | self.redirect={self.redirect}"
        )

    async def __aexit__(self, *args, **kwargs):
        tasks = []

        for transport in self.transports:
            transport.writer.close()
            tasks.append(transport.writer.wait_closed())
        await asyncio.gather(*tasks)


class Client(BaseClient):
    methods = ("GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH")

    async def send_request_directly(self, request: Request):
        transport = await self._get_connection(request.url)
        coro = transport.send_http_request(request.get_raw_request())
        with wrap_errors():
            status_line, header_line, content = await coro
        resp = ResponseParser.parse(status_line, header_line, content)
        resp.request = request
        return resp

    async def _send_request_via_middleware(self, request: Request):
        response = await self.middlewares.process(request, client=self)
        return response

    async def _send_request(
        self,
        url: str,
        method: str,
        content: Union[str, bytearray, bytes] = "",
        params: Union[Iterable[Iterable[str]], None] = None,
        headers: Union[None, Dict[str, str], Headers] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
    ) -> Response:
        headers = Headers(initial_headers=headers)
        request = Request(
            url=url,
            method=method,
            headers=self.headers | headers,
            params=params,
            content=content,
            auth=auth,
            timeout=timeout,
        )
        return await self._send_request_via_middleware(request)

    async def send_request(self, request: Request) -> Response:
        return await self._send_request_via_middleware(
            request=request,
        )

    async def get(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        headers: Union[Dict[str, str], None] = None,
        params: Dict[str, str] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="GET",
            content=content,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
        )

    async def post(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        headers: Union[Dict[str, str], None] = None,
        params: Dict[str, str] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="POST",
            content=content,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
        )

    async def put(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        headers: Union[Dict[str, str], None] = None,
        params: Dict[str, str] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="PUT",
            content=content,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
        )

    async def delete(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        headers: Union[Dict[str, str], None] = None,
        params: Dict[str, str] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="DELETE",
            content=content,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
        )

    async def options(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        headers: Union[Dict[str, str], None] = None,
        params: Dict[str, str] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="OPTIONS",
            content=content,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
        )

    async def head(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        headers: Union[Dict[str, str], None] = None,
        params: Dict[str, str] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="HEAD",
            content=content,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
        )

    async def patch(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        headers: Union[Dict[str, str], None] = None,
        params: Dict[str, str] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
    ) -> Response:
        return await self._send_request(
            url=url,
            method="PATCH",
            content=content,
            headers=headers,
            params=params,
            auth=auth,
            timeout=timeout,
        )


class StreamClient:
    def __init__(self, request):
        self.request = request
        self.transport = None

    async def __aenter__(self):
        request = self.request
        parsed_url = self.request.url
        transport = Transport()
        domain = request.url.get_domain()
        ip, port = await resolve_domain(parsed_url)

        await transport.make_connection(
            ip,
            port,
            **{"ssl": True, "server_hostname": domain}
            if request.url.scheme == "https"
            else {**{"ssl": False, "server_hostname": None}},
        )
        self.transport = transport
        coro = transport.send_http_stream_request(request.get_raw_request())
        iterable = coro.__aiter__()
        status_line, header_line = await iterable.__anext__()
        scheme, status_code, status_message = ResponseParser.parse_status_line(
            status_line
        )
        headers = ResponseParser.parse_and_fill_headers(header_line)
        return StreamResponse(
            status=status_code,
            status_message=status_message,
            content=self.content_iter(iterable),
            headers=headers,
            request=request,
        )

    async def content_iter(self, async_generator: AsyncIterator):
        async for chunk in async_generator:
            yield chunk

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.transport:
            self.transport.writer.close()
            await self.transport.writer.wait_closed()
