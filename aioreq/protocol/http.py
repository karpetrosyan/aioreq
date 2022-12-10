import asyncio
import logging
from abc import ABCMeta, ABC
from abc import abstractmethod
from collections import defaultdict
from typing import Any
from typing import AsyncIterable
from typing import Iterable
from typing import Union

from .encodings import Encoding
from .headers import AcceptEncoding
from .headers import BaseHeader
from ..errors.requests import ConnectionTimeoutError
from ..parser.request_parser import JsonRequestParser
from ..parser.request_parser import RequestParser
from ..parser.response_parser import ResponseParser
from ..parser.url_parser import Url
from ..parser.url_parser import UrlParser
from ..settings import LOGGER_NAME
from ..settings import REQUEST_REDIRECT_COUNT
from ..settings import REQUEST_RETRY_COUNT
from ..settings import TEST_SERVER_DOMAIN
from ..transports.connection import Transport
from ..transports.connection import resolve_domain
from ..utils import debug
from ..utils.generic import wrap_errors

log = logging.getLogger(LOGGER_NAME)


class HttpProtocol(ABC):
    """
    An abstract class for all Http units representing HTTP/1.1 protocol
    with the general attributes
    """

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
        If headers is a Header object, then don't create a new one.
        """
        if isinstance(initial_headers, Headers):
            return initial_headers
        return super(MetaHeaders, cls).__call__(initial_headers)


class Headers(metaclass=MetaHeaders):
    """
    Dict like object used to represent the HTTP headers.
    """

    def __init__(self,
                 initial_headers: Union[dict[str, str], None] = None):
        self._headers = {}
        self.cache = ''

        if initial_headers:
            for key, value in initial_headers.items():
                self[key] = value

    def __setitem__(self, key: str, value: str):
        self.cache = None
        self._headers[key.lower()] = value

    def __getitem__(self, item):
        return self._headers[item.lower()]

    def add_header(self, header: BaseHeader):
        self[header.key] = header.value

    def get_parsed(self):
        if self.cache is not None:
            return self.cache

        headers = (f"{key}:  {value}" for key, value in self._headers.items())
        self.cache = headers
        return headers

    def items(self):
        return self._headers.items()

    def get(self, name, default=None):
        return self._headers.get(name.lower(), default)

    def __contains__(self, item):
        return item.lower() in self._headers

    def __or__(self, other):
        if not isinstance(other, Headers):
            raise ValueError(f"Can't combine {self.__class__.__name__} object with {type(other).__name__}")

        return Headers(
            initial_headers=self._headers | other._headers
        )

    def __len__(self):
        return len(self._headers)

    def __repr__(self):
        return f"Headers:\n" + '\n'.join(
            (f" {key}: {value}" for key, value in self._headers.items())
        )


class BaseRequest(HttpProtocol, metaclass=ABCMeta):
    """
    An abstract class for all HTTP request classes

    This is a low level Request abstraction class which used by Client by default,
    but can be used directly.
    By default, used by 'aioreq.protocol.http.Client.send_request'
    :param method: HTTP method (GET, POST, PUT, PATCH),
    see also RFC[2616] 5.1.1 Method
    :type method: str
    :param headers: HTTP headers paired by (key, value) where 'key'= header name
    and 'value'= header value
    :type headers: dict[str, str]

    :Example:

    >>> from aioreq.protocol.http import Request
    >>> req = Request(
    ...              method='GET',
    ...              host='https://google.com',
    ...              path='/',
    ...              headers={})
    >>> print(req)
    "Request(GET, https://google/com)"
    """

    parser = None

    __slots__ = (
        'method',
        '_host',
        'headers',
        'path',
        'raw_request',
        'content',
        'path_parameters',
    )

    def __init__(
            self,
            url: str,
            *,
            headers: Union[Headers, dict[str, str], None] = None,
            method: str = 'GET',
            raw_request: Union[None, bytes] = None,
            content: Union[str, bytearray, bytes] = '',
            params: Union[Iterable[Iterable[str]], None] = None,
    ) -> None:
        """
        Request initialization method
        """

        if params is None:
            params = ()

        splited_url = UrlParser.parse(url)

        self._host = splited_url.get_url_without_path()
        self.path = splited_url.path

        self.headers = Headers(headers)

        self.method = method
        self.content = content
        self.path_parameters = params
        self._raw_request = raw_request

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, new_value):
        self._host = new_value.strip('/')

    def get_raw_request(self) -> bytes:
        """
        The Getter method for raw_request private attribute if
        request has been pares once, otherwise parse and return

        :returns: raw request for this Request abstraction
        :rtype: bytes
        """

        if self._raw_request:
            return self._raw_request

        message = self.parser.parse(self)
        enc_message = message.encode('utf-8')
        self._raw_request = enc_message
        return enc_message

    def __repr__(self) -> str:
        return f"<Request {self.method} {self.host}>"

    def __getattribute__(self, item):
        self._raw_request = None  # Clear cache
        return super().__getattribute__(item)


class BaseResponse(HttpProtocol, metaclass=ABCMeta):
    """
    An abstract Response class
    """

    __slots__ = (
        'status',
        'status_message',
        'headers',
        'content',
        'request'
    )


class Request(BaseRequest):
    parser = RequestParser


class JsonRequest(BaseRequest):
    parser = JsonRequestParser


class Response(BaseResponse):
    """
    An HTTP response asbtraction

    This is a Response abstraction class used by 'aioreq.parser.response_parser.ResponseParser.parse'
    by default to make response binary data more friendly and not reccommended to use directly
    :param status: response code returned with response,
    see also RFC[2616] 6.1.1 Status Code and Reason Pharse
    :type status: int
    :param status_message: description for :status: in the status line
    :type status_message: str
    :param headers: HTTP headers sent by the server, see also RFC[2616] 6.2
    Response Headers Fields
    :type headers: dict[str, str]
    :param content: response body
    :type content: bytes
    :param request: Request for this response 
    :type request: Request

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
    "Response(200, OK)" 
    """

    def __init__(
            self,
            status: int,
            status_message: str,
            headers: dict[str, str],
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

    def __eq__(self, value: 'Response') -> bool:
        """
        Check if two Response objects have the same attributes or not
        :param value: right side value of equal
        :type value: Response 
        :returns: True if values are equal
        :rtype: bool
        """

        if type(self) != type(value):
            return False
        return self.__dict__ == value.__dict__

    def __repr__(self) -> str:
        return f"<Response {self.status} {self.status_message}>"


class BaseClient(metaclass=ABCMeta):
    """
       A session like class Client used to make requests

       This is a Client abstraction used to communicate with the
       HTTP protocol, send requests, receive responses and so on
       :param headers: HTTP protocol headers
       :type headers: dict[str, str], None
       :param persistent_connections: Persistent connections support for our client
       see also RFC[2616] 8.1 Persistent Connections
       :type persistent_connections: bool
       Header objects defined in 'aioreq.protocol.headers',
       this is an easy way to use HTTP Headers through OOP
       """

    @abstractmethod
    async def _send_request(self,
                            url: str,
                            method: str,
                            content: Union[str, bytearray, bytes] = '',
                            path_parameters: Union[Iterable[Iterable[str]], None] = None,
                            headers: Union[None, dict[str, str], Headers] = None,
                            ) -> Response:
        ...

    @abstractmethod
    async def send_request(self,
                           request: Request, ) -> Response:
        ...

    @staticmethod
    def get_avaliable_encodings():
        return AcceptEncoding(

            *((encoding, 1) for encoding in Encoding.all_encodings)

        )

    def __init__(self,
                 headers: Union[dict[str, str], Headers, None] = None,
                 persistent_connections: bool = False,
                 enable_encodings: bool = True):

        self.connection_mapper = defaultdict(list)

        headers = Headers(initial_headers=headers)

        if enable_encodings and 'accept-encoding' not in headers:
            accept_encoding_object = self.get_avaliable_encodings()
            headers.add_header(accept_encoding_object)

        self.headers = headers
        self.transports = []
        self.persistent_connections = persistent_connections

    async def _get_connection(self, splitted_url: Url):
        """
        Getting connection from already opened connections, to perform Keep-Alive logic,
        if these connections exists or create the new one and save into connection pool
        :param splitted_url: Url object which contains all url parts
        (protocol, version, subdomain, domain, ...)
        :type splitted_url: Url
        :returns: Transport
        """
        transport = None
        if self.persistent_connections:
            log.trace(f"{self.connection_mapper} searching into mapped connections")

            for transport in self.connection_mapper[splitted_url.get_url_for_dns()]:
                if not transport.used:
                    if transport.is_closing():
                        del self.connection_mapper[splitted_url.get_url_for_dns()]
                    else:
                        break
            else:
                transport = None

        if not transport:
            if splitted_url.domain == TEST_SERVER_DOMAIN:  # server for tests
                ip, port = 'localhost', 7575
            else:
                ip = await resolve_domain(splitted_url.get_url_for_dns())
                port = 443 if splitted_url.protocol == 'https' else 80

            transport = Transport()
            connection_coroutine = transport.make_connection(
                ip,
                port,
                ssl=splitted_url.protocol == 'https'
            )
            try:
                await connection_coroutine
                self.transports.append(transport)

            except asyncio.exceptions.TimeoutError as err:
                raise ConnectionTimeoutError('Socket connection timeout') from err

            if self.persistent_connections:
                self.connection_mapper[splitted_url.get_url_for_dns(
                )].append(transport)
        else:
            log.debug("Using already opened connection")
        return transport

    async def __aenter__(self):
        """
        Implements 'with', closes transports after
        session ends

        :returns: Client object
        :type: Client
        """
        return self

    async def __aexit__(self, *args, **kwargs):
        """
        Closes using recourses

        :returns: None
        """
        for fnc, log_data in debug.function_logs.items():
            time = log_data['time']
            call_count = log_data['call_count']
            log.debug(f"Function {fnc.__module__}::{fnc.__name__} log | exec time: {time} | call count: {call_count}")

        tasks = []

        for transport in self.transports:
            transport.writer.close()
            log.trace('Trying to close the connection')
            tasks.append(transport.writer.wait_closed())
        await asyncio.gather(*tasks)
        log.trace('All connections are closed')


class Client(BaseClient):
    """
    :Example:

    >>> import aioreq
    >>> import asyncio
    >>>
    >>> async def main():
    ...     async with aioreq.http.Client() as cl:
    ...         return await cl.get('https://www.youtube.com')
    >>> resp = asyncio.run(main())

    """

    async def get(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0,
            redirect: int = REQUEST_REDIRECT_COUNT,
            retry: int = REQUEST_RETRY_COUNT) -> Response:
        return await self.request_retry_wrapper(
            url=url,
            method="GET",
            content=content,
            headers=headers,
            path_parameters=path_parameters,
            timeout=timeout,
            redirect=redirect + 1,
            retry=retry + 1
        )

    async def post(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0,
            redirect: int = REQUEST_REDIRECT_COUNT,
            retry: int = REQUEST_RETRY_COUNT) -> Response:
        return await self.request_retry_wrapper(
            url=url,
            method="POST",
            content=content,
            headers=headers,
            path_parameters=path_parameters,
            timeout=timeout,
            redirect=redirect + 1,
            retry=retry + 1
        )

    async def put(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0,
            redirect: int = REQUEST_REDIRECT_COUNT,
            retry: int = REQUEST_RETRY_COUNT) -> Response:
        return await self.request_retry_wrapper(
            url=url,
            method="PUT",
            content=content,
            headers=headers,
            path_parameters=path_parameters,
            timeout=timeout,
            redirect=redirect + 1,
            retry=retry + 1
        )

    async def delete(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0,
            redirect: int = REQUEST_REDIRECT_COUNT,
            retry: int = REQUEST_RETRY_COUNT) -> Response:
        return await self.request_retry_wrapper(
            url=url,
            method="DELETE",
            content=content,
            headers=headers,
            path_parameters=path_parameters,
            timeout=timeout,
            redirect=redirect + 1,
            retry=retry + 1
        )

    async def options(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0,
            redirect: int = REQUEST_REDIRECT_COUNT,
            retry: int = REQUEST_RETRY_COUNT) -> Response:
        return await self.request_retry_wrapper(
            url=url,
            method="OPTIONS",
            content=content,
            headers=headers,
            path_parameters=path_parameters,
            timeout=timeout,
            redirect=redirect + 1,
            retry=retry + 1
        )

    async def head(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0,
            redirect: int = REQUEST_REDIRECT_COUNT,
            retry: int = REQUEST_RETRY_COUNT) -> Response:
        return await self.request_retry_wrapper(
            url=url,
            method="HEAD",
            content=content,
            headers=headers,
            path_parameters=path_parameters,
            timeout=timeout,
            redirect=redirect + 1,
            retry=retry + 1
        )

    async def patch(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[dict[str, str], None] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0,
            redirect: int = REQUEST_REDIRECT_COUNT,
            retry: int = REQUEST_RETRY_COUNT) -> Response:
        return await self.request_retry_wrapper(
            url=url,
            method="PATCH",
            content=content,
            headers=headers,
            path_parameters=path_parameters,
            timeout=timeout,
            redirect=redirect + 1,
            retry=retry + 1
        )

    async def send_request_directly(self,
                                    request: Request,
                                    timeout: int = 0):

        splited_url = UrlParser.parse(request.host.strip('/') + request.path)
        transport = await self._get_connection(splited_url)
        coro = transport.send_http_request(request.get_raw_request())
        raw_response, without_body_len = await wrap_errors(coro=coro, timeout=timeout)
        resp = ResponseParser.body_len_parse(raw_response, without_body_len)
        resp.request = request
        return resp

    async def _send_request(self,
                            url: str,
                            method: str,
                            content: Union[str, bytearray, bytes] = '',
                            path_parameters: Union[Iterable[Iterable[str]], None] = None,
                            headers: Union[None, dict[str, str]] = None,
                            timeout: int = 0) -> Response:

        """
        Simulates a http request
        :param url: Url where should be request send
        :type url: str
        :param headers: Http headers which should be used in this GET request
        :type headers: Dict[str, str]
        :param content: Http body part
        :type content: str or bytearray or bytes
        :param method: Http message method
        :type method: str
        :param path_parameters:
        :type path_parameters: Iterable[BaseHeader] or None
        :param timeout: The request timeout
        :type timeout: int
        :returns: Response object which represents returned by server response
        :rtype: Response
        """

        headers = Headers(initial_headers=headers)

        splitted_url = UrlParser.parse(url)
        transport = await self._get_connection(splitted_url)
        request = Request(
            url=url,
            method=method,
            headers=self.headers | headers,
            params=path_parameters,
            content=content,
        )
        coro = transport.send_http_request(request.get_raw_request())
        raw_response, without_body_len = await wrap_errors(coro=coro, timeout=timeout)
        resp = ResponseParser.body_len_parse(raw_response, without_body_len)
        resp.request = request
        return resp

    async def request_redirect_wrapper(self,
                                       *args: tuple[Any],
                                       redirect: int,
                                       **kwargs,
                                       ) -> Response:
        """
        A wrapper method for send_request, also implements redirection if
        3xx status code received
        :param redirect: Maximum request sending counts
        :type redirect: int
        :return: Response object
        :rtype: Response
        """
        request = kwargs.get('request')

        redirect = max(1, redirect)  # minimum one request required

        while redirect != 0:
            redirect -= 1
            if request:
                result = await self.send_request_directly(request)
            else:
                result = await self._send_request(*args, **kwargs)

            if (result.status // 100) == 3:

                if not request:
                    kwargs['url'] = result.headers['Location']
                else:
                    request.host = result.headers['Location']

                if redirect < 1:
                    logging.debug(result, 'last one')
                    return result
            else:
                logging.debug(result)
                return result
            log.info(f'Redirecting request with status code {result.status}')

    async def request_retry_wrapper(self,
                                    *args: tuple[Any],
                                    retry: int,
                                    **kwargs
                                    ) -> Response:
        """
        A wrapper method for request_redirect_wrapper, also implements retrying
        for the requests if they were failed
        :param retry: Maximum request sending count
        :type retry: int
        :return: Response object
        :rtype: Response
        """

        retry = max(1, retry)  # minimum one request required

        while retry != 0:
            retry -= 1
            try:
                result = await self.request_redirect_wrapper(*args, **kwargs)
                return result
            except BaseException as e:
                if retry < 1:
                    raise e
                log.info(f'Retrying request cause of {e}')

    async def send_request(self,
                           request: BaseRequest,
                           timeout: int = 0,
                           redirect: int = REQUEST_REDIRECT_COUNT,
                           retry: int = REQUEST_RETRY_COUNT) -> Response:
        """
        Send request by giving Request object directly
        :param request: Request instance
        :type request: Request
        :param timeout: Request timeout
        :type timeout: int
        :param redirect: Request maximum redirect count
        :type redirect: int
        :param retry: Request retry count
        :type retry: int

        :returns: Response
        :rtype Response:

        """
        return await self.request_retry_wrapper(
            retry=retry,
            redirect=redirect,
            request=request,
            timeout=timeout,
        )


class StreamClient(BaseClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, enable_encodings=False)

    async def _send_request(self,
                            url: str,
                            method: str,
                            content: Union[str, bytearray, bytes] = '',
                            path_parameters: Union[Iterable[Iterable[str]], None] = None,
                            headers: Union[None, dict[str, str]] = None,
                            timeout: int = 0) -> AsyncIterable:
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
            timeout: int = 0):
        async for chunk in self._send_request(
                url=url,
                method="POST",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
                timeout=timeout,
        ):
            yield chunk

    async def get(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[None, dict[str, str]] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0):
        async for chunk in self._send_request(
                url=url,
                method="GET",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
                timeout=timeout,
        ):
            yield chunk

    async def delete(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[None, dict[str, str]] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0):
        async for chunk in self._send_request(
                url=url,
                method="DELETE",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
                timeout=timeout,
        ):
            yield chunk

    async def put(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[None, dict[str, str]] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0):
        async for chunk in self._send_request(
                url=url,
                method="PUT",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
                timeout=timeout,
        ):
            yield chunk

    async def options(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[None, dict[str, str]] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0):
        async for chunk in self._send_request(
                url=url,
                method="OPTIONS",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
                timeout=timeout,
        ):
            yield chunk

    async def patch(
            self,
            url: str,
            content: Union[str, bytearray, bytes] = '',
            headers: Union[None, dict[str, str]] = None,
            path_parameters: Union[Iterable[Iterable[str]], None] = None,
            timeout: int = 0):
        async for chunk in self._send_request(
                url=url,
                method="PATCH",
                content=content,
                headers=headers,
                path_parameters=path_parameters,
                timeout=timeout,
        ):
            yield chunk

    async def send_request(self,
                           request: BaseRequest) -> AsyncIterable:
        splited_url = UrlParser.parse(request.host + request.path)
        transport = await self._get_connection(splited_url)
        coro = transport.send_http_stream_request(request.get_raw_request())
        async for chunk in coro:
            yield chunk
