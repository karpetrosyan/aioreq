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

from ..utils import debug

from typing import Coroutine
from typing import Iterable
from typing import Any
from enum import Enum

from concurrent.futures import ProcessPoolExecutor

log = logging.getLogger(LOGGER_NAME)

class HttpProtocol:
    """
    Abstract class for all Http units representing HTTP/1.1 protocol
    with the general attributes
    """

    safe_methods = (
        "GET",
        "HEAD"
    )


class ImportedParser:

    def __init__(self, value):
        self.module = value

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if self.module is None:
            self.__set__(obj, request_parser.RequestParser)
        return self.module

    def __set__(self, obj, value):
        self.module = value


class BaseRequest(HttpProtocol):
    """
    Base Requets
    """

    parser = ImportedParser(None)
    


class BaseResponse(HttpProtocol):
    """
    Base Response
    """

class Request(BaseRequest):
    """
    Http request Class

    Request class contains all HTTP properties for requesting
    as object attributes.
    Also gives raw encoded data which used to send bytes via socket
    """

    def __init__(
            self,
            method: str,
            host: str,
            headers: dict,
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

        :param method: HTTP method (GET, POST, PUT, PATCH)
        :param host: HTTP header host which contains host's domain
        :param headers: HTTP headers
        :param path: HTTP server endpoint path specified after top-level domain
        :scheme_and_version: HTTP scheme and version
        where HTTP is scheme 1.1 is a version
        :returns: None
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

    def get_raw_request(self) -> bytes:
        """
        Getter method for raw_request private attribute
        """

        if self.__raw_request:
            return self.__raw_request

        self.parser = request_parser.RequestParser

        message = self.parser.parse(self)
        enc_message = message.encode('utf-8')
        self.__raw_request = enc_message
        return enc_message

    def add_header(self, header: Header) -> None:
        self.headers[header.key] = header.value

    def __repr__(self) -> str:
        return '\n'.join((
            f"Request(",
            f"\tscheme_and_version=\'{self.scheme_and_version}\'",
            f"\thost= '{self.host}'",
            f"\tmethod= '{self.method}'",
            f"\tpath= '{self.path}'",
            f"\tHeaders:",
            *(
                f"\t\t{key}: {value}" for key, value in self.headers.items()
            ),
            f"\tBody: {len(self.body)} length"
            ')'
        ))

class Response(BaseResponse):
    """
    Http response Class

    Response class which is one of the first types that
    user using this library can see, it's result for all
    http requests methods like GET, PUT, PATCH, POST
    """

    def __init__(
            self,
            scheme_and_version: str,
            status: int,
            status_message: str,
            headers: dict,
            body: str,
            request: Request | None = None):
        """
        Response initalization method

        :param scheme_and_version: Version and scheme 
        for http. For example HTTP/1.1
        :param status: response code returned with response
        :param status_message: message returned with response status code
        :param headers: response headers for example, Connection : Keep-Alive
        if version lower than HTTP/1.1
        :param body: response body
        :param request: request which response is self
        :returns: None
        """
        self.scheme_and_version = scheme_and_version
        self.status = status
        self.status_message = status_message
        self.headers = headers
        self.body = body
        self.request = request

    def __eq__(self, value) -> bool:
        """
        Check if two Request objects have the same attributes or not

        :param value: right side value of equal
        :returns: True if values are equal
        :rtype: bool
        """

        if type(self) != type(value):
            return False
        return self.__dict__ == value.__dict__

    def __str__(self) -> str:
        return f"Response({self.status}, {self.status_message})"

    def __repr__(self):
        return '\n'.join((
            f"Response(",
            f"\tscheme_and_version='{self.scheme_and_version}'",
            f"\tstatus = {self.status}",
            f"\tstatus_message = '{self.status_message}'",
            f"\tHeaders:",
            *(
                f"\t\t{key}: {value}" for key, value in self.headers.items()
            ),
            f"\tBody: {len(self.body)} length"
            ')'
        ))


class BaseClient(metaclass=ABCMeta):

    @abstractmethod
    async def send_request(self,
                           url: str,
                           method: str,
                           body: str | bytearray | bytes = '',
                           path_parameters: Collection[Iterable[str]] | None = None,
                           headers: None | dict = None,
                           json: dict | None = None) -> Response:...
    async def get(
            self, 
            url : str, 
            body : str | bytearray | bytes= '', 
            headers : None | dict[str, str] = None, 
            json: dict | None = None, 
            path_parameters: None | Collection[tuple[str, str]] = None, 
            obj_headers : None | Iterable[Header] = None,
            timeout: int = 0) -> Response: ...

    async def post(
            self, 
            url : str, 
            body : str | bytearray | bytes= '', 
            headers : None | dict[str, str] = None, 
            json: dict | None = None, 
            path_parameters: None | Collection[tuple[str, str]] = None, 
            obj_headers : None | Iterable[Header] = None,
            timeout: int = 0) -> Response: ...



class Client(BaseClient):
    """
    Session like class Client

    Client used to send requests with same headers or
    send requests using same connections which are stored in
    the Client's connection pool
    """

    def __init__(self,
                 headers : dict[str, str] | None = None,
                 persistent_connections: bool = False,
                 headers_obj: Iterable[Header] | None = None):

        self.connection_mapper = {}
      
        if headers_obj is None:
            headers_obj = [
                    AcceptEncoding(
                            (
                                (Encodings.gzip, ),
                            )         
                                ),
                    ]
        _headers = {}
        
        if headers:
            self.headers =  _headers | headers 
        else:
            self.headers = _headers

        for header in headers_obj:
            self.headers[header.key] = header.value
       
        self.persistent_connections = persistent_connections

    async def get(
            self, 
            url : str, 
            body : str | bytearray | bytes = '', 
            headers : None | dict[str, str] = None, 
            json: dict | None = None, 
            path_parameters: None | Collection[tuple[str, str]] = None, 
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
            path_parameters: None | Collection[tuple[str, str]] = None, 
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
                           path_parameters: Collection[Iterable[str]] | None = None,
                           headers: None | dict[str, str] = None,
                           json: dict | None = None,
                           obj_headers : None | Iterable[Header] = None,
                           timeout: int = 0) -> Response:

        """
        Simulates http request

        :param url: Url where should be request send
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
                                       redirect: str,
                                       **kwargs: dict[str, Any]
                                       ) -> Response:
        """
        Wrapper for send_request method, also implements redirection if
        3xx status code received

        :param redirect: Maximum request sending counts
        
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
        Wrapper for request_redirect_wrapper method, also implements retrying
        for the requests if they were failed

        :param retry: Maximum request sending count
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
        :returns: 'transport'
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
        Implements 'with', close transports after it        

        :returns: Client object
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
