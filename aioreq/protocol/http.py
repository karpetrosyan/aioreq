import asyncio
import logging
import typing
from abc import ABCMeta, ABC
from collections import defaultdict
from typing import AsyncIterable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import TypeVar
from typing import Union

from .headers import BaseHeader
from .middlewares import MiddleWare
from .middlewares import RedirectMiddleWare
from .middlewares import RetryMiddleWare
from .middlewares import default_middlewares
from ..errors.requests import ConnectionTimeoutError
from ..parser.request_parser import BaseRequestParser
from ..parser.request_parser import JsonRequestParser
from ..parser.request_parser import RequestParser
from ..parser.response_parser import ResponseParser
from ..parser.url_parser import Url
from ..parser.url_parser import UrlParser
from ..settings import DEFAULT_TIMEOUT as REQUEST_TIMEOUT
from ..settings import LOGGER_NAME
from ..settings import REQUEST_REDIRECT_COUNT
from ..settings import REQUEST_RETRY_COUNT
from ..settings import TEST_SERVER_DOMAIN
from ..transports.connection import Transport
from ..transports.connection import resolve_domain
from ..utils import debug
from ..utils.generic import wrap_errors

log = logging.getLogger(LOGGER_NAME)

T = TypeVar("T", bound="Headers")
P = TypeVar("P", bound=BaseRequestParser)
TRESP = TypeVar("TRESP", bound='Response')


class HttpProtocol(ABC):
    """
    An abstract class for all Http units representing HTTP/1.1 protocol
    with the general attributes
    """

    __slots__ = tuple()  # type: ignore

    safe_methods = (
        "GET",
        "HEAD"
    )

    scheme = 'HTTP'
    scheme_and_version = 'HTTP/1.1'
    version = '1.1'


class MetaHeaders(type):

    def __call__(cls, initial_headers=None):
        """
        If 'initial headers' passed through 'Headers' is already an instance of 'Headers,'
        return it rather than creating a new one.
        """
        if isinstance(initial_headers, Headers):
            return initial_headers
        return super(MetaHeaders, cls).__call__(initial_headers)


class Headers(metaclass=MetaHeaders):
    """
    The non-case sensitive dictionary.

    :Example:

    >>> from aioreq import Headers
    >>> headers = Headers({'TEST':"TEST"})
    >>> headers['test'] == 'TEST'
    True
    """

    def __init__(self: T,
                 initial_headers: Optional[Union[dict[str, str], T]] = None):
        self._headers: Dict[str, str] = {}
        self.cache: Optional[str] = ''

        if initial_headers:
            for key, value in initial_headers.items():
                self[key] = value

    def __setitem__(self, key: str, value: str):
        """
        :Example:
        >>> headers = Headers({"test": "TEST"})
        >>> parsed = headers.get_parsed()
        >>> bool(headers.cache)
        True
        >>> headers['test'] = "TEST"
        >>> bool(headers.cache)
        False
        """
        self.cache = None
        self._headers[key.lower()] = value

    def __getitem__(self, item):
        return self._headers[item.lower()]

    def add_header(self, header: BaseHeader):
        self[header.key] = header.value

    def get_parsed(self):
        if self.cache is not None:
            return self.cache

        headers = '\r\n'.join(f"{key}:  {value}" for key, value in self._headers.items()) + "\r\n"
        self.cache = headers
        return headers

    def items(self):
        return self._headers.items()

    def get(self, name, default=None):
        return self._headers.get(name.lower(), default)

    def dict(self):
        return self._headers

    def __contains__(self, item):
        return item.lower() in self._headers

    def __or__(self, other):
        if not isinstance(other, Headers):
            raise ValueError(f"Can't combine {self.__class__.__name__} object with {type(other).__name__}")

        return Headers(
            initial_headers=self._headers | other._headers
        )

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if len(self._headers) != len(other.dict()):
            return False
        for header in self._headers:
            if header not in other.dict() or (header and other.dict()[header] != self._headers[header]):
                return False
        return True

    def __len__(self):
        return len(self._headers)

    def __repr__(self):
        return f"Headers:\n" + '\n'.join(
            (f" {key}: {value}" for key, value in self._headers.items())
        )


class BaseRequest(HttpProtocol, metaclass=ABCMeta):
    """
    An abstract class for all 'HttpRequest' classes.

    :param url: Represents the URL as defined in RFC[1738].
    :type url: str
    :param method: Represents the HTTP method as defined in RFC[2616] 5.1.1.
    :type method: str
    :param headers: Represents HTTP headers as described in RFC[2616] 4.2.
    :type headers: dict[str, str] | Headers | None
    :param content: Represents HTTP message body as described in RFC[2616] 4.3.
    :type content: str | bytearray | bytes
    :param params: Represents URL path component as described in RFC[2396] 3.3.
    :type params: Iterable[Iterable[str]] | None
    :param auth: Represents HTTP authentication credentials as described in RFC[7235] 6.2.
    :type auth: Tuple[str, str] | None
    """

    parser: Optional[typing.Type[BaseRequestParser]] = None

    __slots__ = tuple()

    def __init__(
            self,
            url: str,
            *,
            headers: Union[Headers, dict[str, str], None] = None,
            method: str = 'GET',
            content: Union[str, bytearray, bytes] = '',
            params: Union[Iterable[Iterable[str]], None] = None,
            auth: Union[tuple[str, str], None] = None,
            timeout: Union[int, float, None] = None
    ) -> None:
        """
        Request initialization method
        """

        if params is None:
            params = ()

        splited_url = UrlParser.parse(url)

        self._host = splited_url.get_url_without_path()
        self.path = splited_url.path
        self.auth = auth
        self.headers = Headers(headers)
        self.timeout = timeout

        self.method = method
        self.content = content
        self.path_parameters = params
        self._raw_request: Optional[bytes] = None

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, new_value):
        parsed_url = UrlParser.parse(new_value)
        self.path = parsed_url.path
        self._host = parsed_url.get_url_without_path()

    def get_raw_request(self) -> bytes:
        """
        Returns raw bytes that describe the HTTP request to be sent over the network.
        """

        if self._raw_request:
            return self._raw_request

        assert self.parser
        message = self.parser.parse(self)
        enc_message = message.encode('utf-8')
        self._raw_request = enc_message
        return enc_message

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.method} {self.host}>"

    def __getattribute__(self, item):
        self._raw_request = None
        return super().__getattribute__(item)


class BaseResponse(HttpProtocol, metaclass=ABCMeta):
    """
    An abstract class for all 'HttpResponse' classes.
    """

    __slots__ = tuple()


class Request(BaseRequest):
    """
    An HTTP response class.

    :Example:

    >>> from aioreq.protocol.http import Request
    >>> req = Request(
    ...              method='GET',
    ...              url='https://google.com/',
    ...              headers={})
    >>> print(req)
    <Request GET https://google.com>
    """

    __slots__ = (
        'method',
        '_host',
        'headers',
        'path',
        'content',
        'auth',
        'path_parameters',
        '_raw_request',
        'timeout'
    )

    parser = RequestParser


class JsonRequest(BaseRequest):
    """
    :Example:

    >>> from aioreq.protocol.http import Request
    >>> req = JsonRequest(
    ...              method='GET',
    ...              url='https://google.com/',
    ...              headers={})
    >>> print(req)
    <JsonRequest GET https://google.com>
    """

    __slots__ = (
        'method',
        '_host',
        'headers',
        'path',
        'content',
        'auth',
        'path_parameters',
        '_raw_request',
        'timeout'
    )

    parser = JsonRequestParser


class Response(BaseResponse):
    """
    An HTTP response class.

    :param status: Represents the HTTP status code as defined in RFC[2616] 6.1.1.
    :type status: int
    :param status_message: Represents the HTTP reason phrase as defined in RFC[2616] 6.1.1.
    :type status_message: str
    :param headers: Represents HTTP headers as described in RFC[2616] 4.2.
    :type headers: Headers
    :param content: Represents HTTP message body as described in RFC[2616] 4.3.
    :type content: bytes
    :param request: Http request, instance of BaseRequest
    :type request: BaseRequest | None

    :Example:

    >>> import aioreq
    >>> from aioreq.protocol.http import Response
    >>> 
    >>> a = Response(
    ...          status=200,
    ...          status_message='OK',
    ...          headers={},
    ...          content=b'Test message',
    ...          request=None)
    >>> print(a)
    <Response 200 OK>
    """

    __slots__ = (
        'status',
        'status_message',
        'headers',
        'content',
        'request'
    )

    def __init__(
            self,
            status: int,
            status_message: str,
            headers: Headers | dict[str, str],
            content: bytes,
            request: Union[Request, None] = None):
        """
        Response initialization method
        """

        self.status = status
        self.status_message = status_message
        self.headers = Headers(headers)
        self.content = content
        self.request = request

    def __eq__(self, _value) -> bool:  # type: ignore
        """
        Checks if two Response objects have the same attributes or not
        :param _value: right side value of equal
        :type _value: Response 
        :returns: True if values are equal
        :rtype: bool

        :Example:

        >>> a = Response(
        ...          status=200,
        ...          status_message='OK',
        ...          headers={},
        ...          content=b'Test message',
        ...          request=None)
        >>> b = Response(
        ...          status=200,
        ...          status_message='OK',
        ...          headers={'test': 'test'},
        ...          content=b'Test message')
        >>> a == b
        False
        >>> c = Response(
        ...          status=200,
        ...          status_message='OK',
        ...          headers={},
        ...          content=b'Test message',
        ...          request=None)
        >>> a == c
        True
        """

        if type(self) != type(_value):
            raise TypeError("Can't compare `{type(self).__name__}` with `{type(_value).__name__}`")
        return self.status == _value.status and self.status_message == _value.status_message and \
            self.headers == _value.headers and self.content == _value.content and self.request == _value.request

    def __repr__(self) -> str:
        return f"<Response {self.status} {self.status_message}>"


class BaseClient(metaclass=ABCMeta):
    """
    The client's base class.

    :param headers: Represents HTTP headers as described in RFC[2616] 4.2.
    :type headers: Headers | None | dict[str, str]
    :param persistent_connections: Represents HTTP persistent connections described in RFC[2616] 8.1
    :type persistent_connections: bool
    :param redirect_count: Default redirect count for the request.
    :type redirect_count: int
    :param retry_count: Default retry count for the request.
    :type retry_count: int
    :param auth: Represents HTTP authentication credentials as described in RFC[7235] 6.2.
    :type auth: Tuple[str, str] | None
    :param middlewares: A collection of 'aioreq' middlewares.
    :type middlewares: Tuple[str] | None

    Header objects defined in 'aioreq.protocol.headers',
    this is an easy way to use HTTP Headers through OOP
    """

    def __init__(self,
                 headers: Union[dict[str, str], Headers, None] = None,
                 persistent_connections: bool = False,
                 redirect_count: int = REQUEST_REDIRECT_COUNT,
                 retry_count: int = REQUEST_RETRY_COUNT,
                 timeout: Union[int, float, None] = None,
                 auth: Union[tuple[str, str], None] = None,
                 middlewares: Optional[typing.Tuple[Union[str, typing.Type[MiddleWare]], ...]] = None):

        headers = Headers(initial_headers=headers)

        RedirectMiddleWare.redirect_count = redirect_count
        RetryMiddleWare.retry_count = retry_count

        if middlewares is None:
            self.middlewares = MiddleWare.build(default_middlewares)
        else:
            self.middlewares = MiddleWare.build(middlewares)
        if timeout is None:
            timeout = REQUEST_TIMEOUT

        self.timeout = timeout
        self.redirect = redirect_count
        self.retry = retry_count
        self.auth = auth
        self.connection_mapper: defaultdict[str, list] = defaultdict(list)
        self.headers = headers
        self.transports: List[Transport] = []
        self.persistent_connections = persistent_connections

    async def _get_connection(self, url: Url):
        """
        Gets connections from previously opened connections in order to perform Keep-Alive logic 
        if these connections exist, or creates new ones and saves them to the connection pool.
        
        :param url: Represents the URL as defined in RFC[1738].
        :type url: str
        """
        transport = None
        if self.persistent_connections:
            log.trace(f"{self.connection_mapper} searching into mapped connections")  # type: ignore

            for transport in self.connection_mapper[url.get_url_for_dns()]:
                if not transport.used:
                    if transport.is_closing():
                        del self.connection_mapper[url.get_url_for_dns()]
                    else:
                        break
            else:
                transport = None

        if not transport:
            if url.domain == TEST_SERVER_DOMAIN:  # server for tests
                ip, port = 'localhost', 7575
            else:
                ip = await resolve_domain(url.get_url_for_dns())
                port = 443 if url.protocol == 'https' else 80

            transport = Transport()
            connection_coroutine = transport.make_connection(
                ip,
                port,
                ssl=url.protocol == 'https'
            )
            try:
                await connection_coroutine
                self.transports.append(transport)

            except asyncio.exceptions.TimeoutError as err:
                raise ConnectionTimeoutError('Socket connection timeout') from err

            if self.persistent_connections:
                self.connection_mapper[url.get_url_for_dns(
                )].append(transport)
        else:
            log.debug("Using already opened connection")
        return transport

    async def __aenter__(self):
        """
        Implements 'with', closes transports after session ends
        """
        return self

    def __str__(self):
        return (
            f'{self.headers}'
            f'\n{self.persistent_connections=}'
            f'\n{self.retry=} | {self.redirect=}'
        )

    async def __aexit__(self, *args, **kwargs):
        """
        Closes using recourses
        """
        for fnc, log_data in debug.function_logs.items():
            time = log_data['time']
            call_count = log_data['call_count']
            log.debug(f"Function {fnc.__module__}::{fnc.__name__} log | exec time: {time} | call count: {call_count}")

        tasks = []

        for transport in self.transports:
            assert transport.writer
            transport.writer.close()
            log.trace('Trying to close the connection')  # type: ignore
            tasks.append(transport.writer.wait_closed())
        await asyncio.gather(*tasks)
        log.trace('All connections are closed')  # type: ignore


class Client(BaseClient):
    """
    An HTTP client class.

    :Example:

    >>> import aioreq
    >>> import asyncio
    >>>
    >>> async def main():
    ...     async with aioreq.http.Client() as cl:
    ...         return await cl.get('https://www.youtube.com')
    >>> resp = asyncio.run(main())

    """

    async def send_request_directly(self,
                                    request: Request):
        splited_url = UrlParser.parse(request.host.strip('/') + request.path)
        transport = await self._get_connection(splited_url)
        coro = transport.send_http_request(request.get_raw_request())
        raw_response, without_body_len = await wrap_errors(coro=coro)
        resp = ResponseParser.body_len_parse(raw_response, without_body_len)
        resp.request = request
        return resp

    async def _send_request_via_middleware(self,
                                           request: Request):
        response = await self.middlewares.process(request, client=self)
        return response

    async def _send_request(self,
                            url: str,
                            method: str,
                            content: Union[str, bytearray, bytes] = '',
                            params: Union[Iterable[Iterable[str]], None] = None,
                            headers: Union[None, dict[str, str], Headers] = None,
                            auth: Union[tuple[str, str], None] = None,
                            timeout: Union[int, float, None] = None
                            ) -> Response:
        """
        Simulates a http request
        :param url: Represents the URL as defined in RFC[1738].
        :type url: str
        :param method: Represents the HTTP method as defined in RFC[2616] 5.1.1.
        :type method: str
        :param content: Represents HTTP message body as described in RFC[2616] 4.3.
        :type content: str | bytearray | bytes
        :param params: Represents URL path component as described in RFC[2396] 3.3.
        :type params: Iterable[Iterable[str]] | None
        :param headers: Represents HTTP headers as described in RFC[2616] 4.2.
        :type headers: dict[str, str] | Headers | None
        :param params:
        :returns: An HTTP response instance
        :rtype: Response
        """

        headers = Headers(initial_headers=headers)

        request = Request(
            url=url,
            method=method,
            headers=self.headers | headers,
            params=params,
            content=content,
            auth=auth,
            timeout=timeout
        )
        return await self._send_request_via_middleware(request)

    async def send_request(self, request: Request) -> Response:
        """
        Sends request by giving Request object via middleware.

        :param request: An HTTP request instance
        :type request: Request
        :returns: An HTTP response instance
        :rtype Response:

        """
        return await self._send_request_via_middleware(
            request=request,
        )

    async def get(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            auth: Union[tuple[str, str], None] = None,
            timeout: Union[int, float, None] = None
    ) -> Response:
        return await self._send_request(
            url=url,
            method="GET",
            content=content,
            headers=headers,
            params=path_parameters,
            auth=auth,
            timeout=timeout
        )

    async def post(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            auth: Union[tuple[str, str], None] = None,
            timeout: Union[int, float, None] = None
    ) -> Response:
        return await self._send_request(
            url=url,
            method="POST",
            content=content,
            headers=headers,
            params=path_parameters,
            auth=auth,
            timeout=timeout
        )

    async def put(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            auth: Union[tuple[str, str], None] = None,
            timeout: Union[int, float, None] = None
    ) -> Response:
        return await self._send_request(
            url=url,
            method="PUT",
            content=content,
            headers=headers,
            params=path_parameters,
            auth=auth,
            timeout=timeout
        )

    async def delete(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            auth: Union[tuple[str, str], None] = None,
            timeout: Union[int, float, None] = None
    ) -> Response:
        return await self._send_request(
            url=url,
            method="DELETE",
            content=content,
            headers=headers,
            params=path_parameters,
            auth=auth,
            timeout=timeout
        )

    async def options(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            auth: Union[tuple[str, str], None] = None,
            timeout: Union[int, float, None] = None
    ) -> Response:
        return await self._send_request(
            url=url,
            method="OPTIONS",
            content=content,
            headers=headers,
            params=path_parameters,
            auth=auth,
            timeout=timeout
        )

    async def head(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            auth: Union[tuple[str, str], None] = None,
            timeout: Union[int, float, None] = None
    ) -> Response:
        return await self._send_request(
            url=url,
            method="HEAD",
            content=content,
            headers=headers,
            params=path_parameters,
            auth=auth,
            timeout=timeout
        )

    async def patch(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            auth: Union[tuple[str, str], None] = None,
            timeout: Union[int, float, None] = None
    ) -> Response:
        return await self._send_request(
            url=url,
            method="PATCH",
            content=content,
            headers=headers,
            params=path_parameters,
            auth=auth,
            timeout=timeout
        )


class StreamClient(BaseClient):

    async def _send_request(self,
                            url: str,
                            method: str,
                            content: Union[str, bytearray, bytes] = '',
                            path_parameters: Union[Iterable[Iterable[str]], None] = None,
                            headers: Union[None, dict[str, str], Headers] = None,
                            ) -> AsyncIterable:
        headers = Headers(initial_headers=headers)

        request = Request(
            url=url,
            method=method,
            headers=self.headers | headers,
            params=path_parameters,
            content=content,
        )
        async for chunk in self.send_request(request):
            yield chunk

    async def post(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[None, dict[str, str]] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
    ):
        async for chunk in self._send_request(
                url=url,
                method="POST",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
        ):
            yield chunk

    async def get(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[None, dict[str, str]] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None):
        async for chunk in self._send_request(
                url=url,
                method="GET",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
        ):
            yield chunk

    async def delete(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[None, dict[str, str]] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None):
        async for chunk in self._send_request(
                url=url,
                method="DELETE",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
        ):
            yield chunk

    async def put(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[None, dict[str, str]] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None, ):
        async for chunk in self._send_request(
                url=url,
                method="PUT",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
        ):
            yield chunk

    async def options(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[None, dict[str, str]] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None, ):
        async for chunk in self._send_request(
                url=url,
                method="OPTIONS",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
        ):
            yield chunk

    async def patch(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[None, dict[str, str]] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None):
        async for chunk in self._send_request(
                url=url,
                method="PATCH",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
        ):
            yield chunk

    async def send_request(self,
                           request: BaseRequest) -> AsyncIterable:
        splited_url = UrlParser.parse(request.host + request.path)
        transport = await self._get_connection(splited_url)
        coro = transport.send_http_stream_request(request.get_raw_request())
        async for chunk in coro:
            yield chunk
