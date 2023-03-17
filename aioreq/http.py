import asyncio
import logging
from abc import ABCMeta
from collections import defaultdict
from typing import Any
from typing import AsyncGenerator
from typing import AsyncIterator
from typing import DefaultDict
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

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

from .headers import Headers
from .middlewares import MiddleWare
from .middlewares import RedirectMiddleWare
from .middlewares import RetryMiddleWare
from .middlewares import default_middlewares
from .settings import DEFAULT_HEADERS

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
        content: Union[str, bytes, bytearray, None] = None,
        params: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
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
        )


class Response(BaseResponse):
    """This object represents a simple HTTP response."""

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
    """Represents a Streaming Response that can
    iterate through the incoming data asynchronously."""

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
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Union[None, Dict[str, str], Headers] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
    ) -> BaseRequest:
        """Creates one of the "Request" instances based on attributes."""

        headers = Headers(initial_headers=headers)
        content_found = False

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
            request_class: Type[BaseRequest] = JsonRequest  # type: ignore
        elif urlencoded:
            request_class: Type[BaseRequest] = UrlEncodedRequest  # type: ignore

            content = urlencoded  # type: ignore
        else:
            request_class: Type[BaseRequest] = Request  # type: ignore

        request = request_class(  # type: ignore
            url=url,
            method=method,
            headers=self.headers | headers,
            params=params,
            content=content,
            auth=auth,
            timeout=timeout,
            check_hostname=check_hostname,
            verify_mode=verify_mode,
            keylog_filename=keylog_filename,
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
        coro = transport.send_http_request(request.get_raw_request())
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
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Union[None, Dict[str, str], Headers] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
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
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
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
        )

    async def post(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
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
        )

    async def put(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
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
        )

    async def delete(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
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
        )

    async def options(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
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
        )

    async def head(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
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
        )

    async def patch(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
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
        )

    async def link(
        self,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
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
        )


class StreamClient(BaseClient):
    def __init__(self, request):
        self.request = request
        self.transport = None
        super().__init__()

    @classmethod
    def get(
        cls,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
    ):
        self = cls(None)
        request = self._build_request(
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
        )
        self.request = request
        return self

    @classmethod
    def post(
        cls,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
    ):
        self = cls(None)
        request = self._build_request(
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
        )
        self.request = request
        return self

    @classmethod
    def put(
        cls,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
    ):
        self = cls(None)
        request = self._build_request(
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
        )
        self.request = request
        return self

    @classmethod
    def delete(
        cls,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
    ):
        self = cls(None)
        request = self._build_request(
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
        )
        self.request = request
        return self

    @classmethod
    def patch(
        cls,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
    ):
        self = cls(None)
        request = self._build_request(
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
        )
        self.request = request
        return self

    @classmethod
    def options(
        cls,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
    ):
        self = cls(None)
        request = self._build_request(
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
        )
        self.request = request
        return self

    @classmethod
    def head(
        cls,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
    ):
        self = cls(None)
        request = self._build_request(
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
        )
        self.request = request
        return self

    @classmethod
    def link(
        cls,
        url: str,
        content: Union[str, bytearray, bytes] = "",
        json: Optional[Dict] = None,
        urlencoded: Union[Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        headers: Union[Dict[str, str], None] = None,
        params: Union[Dict[str, str], None] = None,
        auth: Union[Tuple[str, str], None] = None,
        timeout: Union[int, float, None] = None,
        check_hostname: bool = True,
        verify_mode: bool = True,
        keylog_filename: Optional[str] = None,
    ):
        self = cls(None)
        request = self._build_request(
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
        )
        self.request = request
        return self

    async def __aenter__(self) -> StreamResponse:
        """
        Creates the Request instance and sends it through the stream, returning
        a StreamResponse instance with status code, status message, headers,
        and content that can be iterated asynchronously.
        """
        request = self.request
        parsed_url = self.request.url
        transport = Transport()
        domain = request.url.get_domain()
        ip, port = await resolve_domain(parsed_url)

        await transport.make_connection(
            ip,
            port,
            ssl=request.url.scheme == "https",
            server_hostname=domain,
            check_hostname=request.check_hostname,
            verify_mode=request.verify_mode,
            keylog_filename=request.keylog_filename,
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
            content=self._content_iter(iterable),
            headers=headers,
            request=request,
        )

    async def _content_iter(self, async_generator: AsyncIterator[bytes]):
        async for chunk in async_generator:
            yield chunk

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.transport:
            if not self.transport.is_closing():
                self.transport.writer.close()
                await self.transport.writer.wait_closed()
