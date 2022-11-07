import ssl
import time
import logging
import asyncio
import certifi
import json as _json

from abc import ABCMeta
from abc import abstractmethod

from collections.abc import Collection
from ..protocol.headers import Header

from ..errors.requests import AsyncRequestsError

from ..parser.url_parser import UrlParser
from ..parser.response_parser import ResponseParser
from ..parser import request_parser

from ..transports.connection import resolve_domain
from ..transports.connection import Transport 

from ..settings import LOGGER_NAME
from ..settings import DEFAULT_CONNECTION_TIMEOUT

from ..errors.requests import RequestTimeoutError
from ..errors.requests import ConnectionTimeoutError

from .headers import TransferEncoding
from .headers import AcceptEncoding
from .headers import Header

from .encodings import Encodings
from .encodings import Encoding

from ..utils import debug

from typing import Coroutine
from typing import Iterable
from typing import Any
from enum import Enum

from concurrent.futures import ProcessPoolExecutor

log = logging.getLogger(LOGGER_NAME)

class HttpProtocol(metaclass=ABCMeta):
    """
    An abstract class for all Http units representing HTTP/1.1 protocol
    with the general attributes
    """

    safe_methods = (
        "GET",
        "HEAD"
    )

class BaseRequest(HttpProtocol, metaclass=ABCMeta):
    """
    An abstract Request class 
    """

    @abstractmethod
    def get_raw_request(self) -> bytes: ...


class BaseResponse(HttpProtocol, metaclass=ABCMeta):
    """
    An abstract Response class
    """

class Request(BaseRequest):
    """
    An HTTP request abstraction 

    This is a low level Request abstraction class which used by Client by default,
    but can be used directly.
    By default used by 'aioreq.protocol.http.Client.send_request' 

    :param method: HTTP method (GET, POST, PUT, PATCH),
    see also RFC[2616] 5.1.1 Method
    :type method: str
    :param host: HTTP header host which contains host's domain,
    see also RFC[2616] 14.23 Host
    :type host: str
    :param headers: HTTP headers paired by (key, value) where 'key'= header name
    and 'value'= header value
    :type headers: dict[str, str]
    :param path: HTTP server endpoint path specified after top-level domain
    :type path: str
    :scheme_and_version: HTTP scheme and version

    :Example:

    >>> from aioreq.protocol.http import Request
    >>> req = Request(
    >>>              method='GET',
    >>>              host='https://google.com',
    >>>              path='/',
    >>>              headers={})
    >>> print(req)
    "Request(GET, https://google/com)"

    .. todo:: Remove version properties
    """

    def __init__(
            self,
            method: str,
            host: str,
            headers: dict['str', 'str'],
            path: str,
            raw_request: None | bytes = None,
            body: str | bytearray | bytes = '',
            json: dict | None = None,
            path_parameters: Iterable[Iterable[str]] | None = None,
            scheme: str = 'HTTP',
            version: str = '1.1',
            scheme_and_version: str = 'HTTP/1.1',
    ) -> None:
        """
        Request initialization method
        """

        if path_parameters is None:
            path_parameters = ()

        if body and json:
            raise ValueError(
                "Body and Json attributes was"
                "given but there is only one needed"
            )

        self.host = host
        self.headers = headers
        self.method = method
        self.path = path
        self.body = body
        self.json = json
        self.path_parameters = path_parameters
        self.scheme = scheme
        self.version = version
        self.scheme_and_version = scheme_and_version
        self.__raw_request = raw_request
        self.parser = request_parser.RequestParser

    def get_raw_request(self) -> bytes:
        """
        The Getter method for raw_request private attribute

        :returns: raw request for this Request abstraction
        :rtype: bytes
        """

        if self.__raw_request:
            return self.__raw_request

        message = self.parser.parse(self)
        enc_message = message.encode('utf-8')
        self.__raw_request = enc_message
        return enc_message

    def add_header(self, header: Header) -> None:
        self.headers[header.key] = header.value

    def __repr__(self) -> str:
        return f"<Request {self.method} {self.host}>"

class Response(BaseResponse):
    """
    An HTTP response asbtraction

    This is a Response abstraction class used by 'aioreq.parser.response_parser.ResponseParser.parse'
    by default to make response binary data more friendly and not reccommended to use directly.

    :param scheme_and_version: Version and scheme 
    :type scheme_and_version: str
    :param status: response code returned with response,
    see also RFC[2616] 6.1.1 Status Code and Reason Pharse
    :type status: int
    :param status_message: description for :status: in the status line
    :type status_message: str
    :param headers: HTTP headers sent by the server, see also RFC[2616] 6.2
    Response Headers Fields
    :type headers: dict[str, str]
    :param body: response body
    :type body: bytes
    :param request: Request for this response 
    :type request: Request

    :Example:

    >>> import aioreq
    >>> from aioreq.protocol.http import Response
    >>> 
    >>> a = Response(scheme_and_version='HTTP/1.1',
    >>>          status=200,
    >>>          status_message='OK',
    >>>          headers={},
    >>>          body=b'Test message',
    >>>          request=None)
    >>> print(a)
    "Response(200, OK)" 
    """

    def __init__(
            self,
            scheme_and_version: str,
            status: int,
            status_message: str,
            headers: dict,
            body: bytes,
            request: Request | None = None):
        """
        Response initalization method
        """

        self.scheme_and_version = scheme_and_version
        self.status = status
        self.status_message = status_message
        self.headers = headers
        self.body = body
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
    An abstract class for all Clients
    """

    @abstractmethod
    async def send_request(self,
                           url: str,
                           method: str,
                           body: str | bytearray | bytes = '',
                           path_parameters: Iterable[Iterable[str]] | None = None,
                           headers: None | dict = None,
                           json: dict | None = None) -> Response:...

class Client(BaseClient):
    """
    A session like class Client used to make requests 

    This is a Client abstraction used to communicate with the
    HTTP protocol, send requests, receive responses and so on

    :param headers: HTTP protocol headers
    :type headers: dict[str, str], None
    :param persistent_connections: Persistent connections support for our client
    see also RFC[2616] 8.1 Persistent Connections
    :type persistent_connections: bool
    :param headers_obj: Iterable object which contains
    Header objects defined in 'aioreq.protocol.headers',
    this is an easy way to use HTTP Headers through OOP
    """

    def __init__(self,
                 headers : dict[str, str] | None = None,
                 persistent_connections: bool = False,
                 headers_obj: Iterable[Header] | None = None):

        self.connection_mapper = {}
      
        if headers_obj is None:
            headers_obj = [
                    AcceptEncoding(
                            [
                                (encoding, ) for encoding in Encoding.all_encodings
                                ]         
                                ),
                    ]
        _headers = {}

        for header in headers_obj:
            _headers[header.key] = header.value
       
        if headers:
            self.headers =  _headers | headers 
        else:
            self.headers = _headers
       
        self.persistent_connections = persistent_connections

    async def get(
            self, 
            url : str, 
            body : str | bytearray | bytes = '', 
            headers : None | dict[str, str] = None, 
            json: dict | None = None, 
            path_parameters: None | Iterable[Iterable[str]] = None, 
            obj_headers : None | Iterable[Header] = None,
            timeout: int = 0,
            redirect: int = 3,
            retry: int = 3) -> Response:
        return await self.request_retry_wrapper(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters,
            obj_headers=obj_headers,
            timeout=timeout,
            redirect=redirect+1,
            retry=retry+1
        )

    async def post(
            self, 
            url : str, 
            body : str | bytearray | bytes= '', 
            headers : None | dict[str, str] = None, 
            json: dict | None = None, 
            path_parameters: None | Iterable[Iterable[str]] = None, 
            obj_headers : None | Iterable[Header] = None,
            timeout: int = 0,
            redirect: int = 3,
            retry: int = 3) -> Response:
        return await self.request_retry_wrapper(
            url=url,
            method="POST",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters,
            obj_headers=obj_headers,
            timeout=timeout,
            redirect=redirect+1,
            retry=retry+1
        )

    async def send_request(self,
                           url: str,
                           method: str,
                           body: str | bytearray | bytes = '',
                           path_parameters: Iterable[Iterable[str]] | None = None,
                           headers: None | dict[str, str] = None,
                           json: dict | None = None,
                           obj_headers : None | Iterable[Header] = None,
                           timeout: int = 0) -> Response:

        """
        Simulates an http request

        :param url: Url where should be request send
        :type url: str
        :param headers: Http headers which should be used in this GET request
        :param body: Http body part
        :param method: Http message method
        :param path_parameters:
        :returns: Response object which represents returned by server response
        """

        if headers is None:
            headers = {}

        splited_url = UrlParser.parse(url)
        transport = await self.get_connection( splited_url )
        request = Request(
            method=method,
            host=splited_url.get_url_without_path(),
            headers=self.headers | headers,
            path=splited_url.path,
            path_parameters=path_parameters,
            json=json,
            body=body,
            scheme='HTTP'
        )
        coro = transport.send_http_request(request.get_raw_request())
        if timeout == 0:
            raw_response = await coro 
        else:
            try:
                raw_response = await asyncio.wait_for(coro, timeout=timeout)
            except asyncio.exceptions.TimeoutError as e:
                raise RequestTimeoutError("Request timeout error")
            except BaseException as e:
                raise e

        response = ResponseParser.parse(raw_response)
        response.request = request
        return response

    async def request_redirect_wrapper(self,
                                       *args: tuple[Any],
                                       redirect: int,
                                       **kwargs: dict[str, Any]
                                       ) -> Response:
        """
        A wrapper method for send_request, also implements redirection if
        3xx status code received

        :param redirect: Maximum request sending counts
        :type redirect: int
        :return: Response object
        :rtype: Response
        """

        redirect = max(1, redirect) # minimum one request required

        while redirect != 0:
            redirect -= 1
            result = await self.send_request(*args, **kwargs)

            if (result.status // 100) == 3:
                kwargs['url'] = result.headers['Location']
                if redirect < 1:
                    return result
            else:
                return result
            log.info(f'Redirecting reuqest with status code {result.status}')
                    
    async def request_retry_wrapper(self,
                                    *args: tuple[Any],
                                    retry: int,
                                    **kwargs: dict[str, Any]
                                    ) -> Response:
        """
        A wrapper method for request_redirect_wrapper, also implements retrying
        for the requests if they were failed

        :param retry: Maximum request sending count
        :type retry: int
        :return: Response object
        :rtype: Response
        """

        retry = max(1, retry) # minimum one request required

        while retry != 0:
            retry -= 1
            try:
                result = await self.request_redirect_wrapper(*args, **kwargs)
                return result
            except BaseException as e:
                if retry < 1:
                    raise e
                raise e
                log.info(f'Retrying request cause of {e}')

    async def get_connection(self, splited_url):
        """
        Getting connection from already opened connections, to perform Keep-Alive logic,
        if these connections exists or create the new one and save into connection pool

        :param splited_url: Url object which contains all url parts
        (scheme, version, subdomain, domain, ...)
        :type splited_url: Url
        :returns: Transport
        """

        if self.persistent_connections:
            log.debug(f"{self.connection_mapper} searching into mapped connections")
            transport = self.connection_mapper.get(
                splited_url.get_url_for_dns(), None)
                
            if transport:
                if transport.is_closing():
                    transport = None 
                elif transport.used:
                    raise AsyncRequestsError("Can't use persistent connections without pipelining")
        
        else:
            transport = None

        if not transport:
            if splited_url.domain == 'testulik': # server for tests
                ip, port = '127.0.0.1', 7575
            else:
                ip = await resolve_domain(splited_url.get_url_for_dns())
                port = 443 if splited_url.scheme == 'https' else 80

            loop = asyncio.get_running_loop()

            transport = Transport()
            connection_coroutine = transport.make_connection(
                    ip,
                    port,
                    ssl = splited_url.scheme == 'https'
                    )
            try:
                await connection_coroutine
            except asyncio.exceptions.TimeoutError as err:
                raise ConnectionTimeoutError('Socket connection timeout') from err

            if self.persistent_connections:
                self.connection_mapper[splited_url.get_url_for_dns(
                    )] = transport 
        else:
            log.info("Using already opened connection")
        return transport 

    async def __aenter__(self):
        """
        Implements 'with', close transports after
        session ends

        :returns: Client object
        :type: Client
        """
        return self

    async def __aexit__(self, *args, **kwargs):
        """
        Close using recourses

        :returns: None
        """

        for host, transport in self.connection_mapper.items():
            transport.writer.close()
            await transport.writer.wait_closed()
            log.info(f"Transport closed {transport=}")
