import logging
import asyncio
import json as _json

from abc import abstractmethod
from ..parser.url_parser import UrlParser
from ..parser.response_parser import ResponseParser
from ..parser import request_parser
from ..socket.connection import resolve_domain
from ..socket.connection import HttpClientProtocol
from ..settings import LOGGER_NAME
from ..settings import DEFAULT_CONNECTION_TIMEOUT
from ..socket.buffer import HttpBuffer
from typing import Iterable
from enum import Enum

log = logging.getLogger(LOGGER_NAME)

class BodyReceiveStrategies(Enum):
    chunked = 'chunked'
    content_length = 'content_length'


class HttpProtocol:
    """
    Abstract class for all Http units representing HTTP/1.1 protocol
    with the general attributes
    """

    safe_methods = (
        "GET",
        "HEAD"
    )


class BaseRequest(HttpProtocol):
    """
    Base Requets
    """


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
            json: str = '',
            path_parameters: Iterable[Iterable[str]] | None = None,
            scheme_and_version: str = 'HTTP/1.1',
            parser: request_parser.RequestParser | None = None
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

        self.host = host
        self.headers = headers
        self.method = method
        self.path = path
        self.body = body
        self.json = json
        self.path_parameters = path_parameters
        self.scheme_and_version = scheme_and_version
        self.__raw_request = raw_request
        self.parser = parser

        if self.parser is None:
            self.parser = request_parser.RequestParser

    def get_raw_request(self) -> bytes:
        """
        Getter method for raw_request private attribute
        """

        if self.__raw_request:
            return self.__raw_request

        if self.parser is None:
            from ..parser import request_parser
            self.parser = request_parser.RequestParser

        message = self.parser.parse(self)
        enc_message = message.encode('utf-8')
        self.__raw_request = enc_message
        return enc_message

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

class PendingMessage:

    def __init__(self,
                 text: str) -> None:
        self.text = text
        self.__headers_done: bool = False
        self.body_receiving_strategy: BodyReceiveStrategies | None = None
        self.body_start: int | None = None
        self.content_length: int | None = None
        self.bytes_should_receive: int = 0 

    def headers_done(self) -> bool:
        """
        Check if text contains HTTP message data included full headers
        or there is headers coming now
        """

        if not self.__headers_done:
            is_done = ResponseParser.headers_done(self.text)
            log.info(f"{is_done=}")
            if is_done:
                self.body_start = ResponseParser.get_without_body_length(self.text)
            self.__headers_done = is_done
        return self.__headers_done

    def parse_by_content_length(self) -> None | int:
        if len(self.text) >= self.body_start + self.content_length:
            return self.body_start + self.content_length
            
    def parse_by_chunk(self) -> None | int:
        
        log.info('Parsing by chunks')
        if self.bytes_should_receive:
            if self.body_start + self.bytes_should_receive <= len(self.text):
                self.body_start += self.bytes_should_receive
                self.bytes_should_receive = 0
        else:
            for pattern in ResponseParser.regex_end_chunks:
                end_match = pattern.search(self.text)
                if end_match:
                    self.body_start += end_match.end() - end_match.start()
                    return self.body_start

            match = ResponseParser.regex_find_chunk.serach(self.text)
            if match is None:
                return
            size = int(match.group('content_size'))
            self.bytes_should_receive += size


    def find_strategy(self) -> None:
        content_length = ResponseParser.search_content_length(self.text)
        if content_length is not None:
            self.content_length = content_length
            self.body_receiving_strategy = BodyReceiveStrategies('content_length')
        else:
            self.body_receiving_strategy = BodyReceiveStrategies('chunked')
        log.info(f"Strategy for {self.text=} is {self.body_receiving_strategy=}")

    def add_data(self, text: str) -> None | int:
        log.info(f"Got {text=}")
        self.text += text

        if self.headers_done():
             
            if not self.body_receiving_strategy:
                self.find_strategy()

            match self.body_receiving_strategy.value:
                
                case 'chunked':
                    parse_fnc = self.parse_by_chunk
                case 'content_length':
                    parse_fnc = self.parse_by_content_length
                case _:
                    assert False, "Strategy not found"
            result = parse_fnc()
            if result and isinstance(result, int):
                log.info(f"Got result {self.text[:result]}")
                return self.text[:result]


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


class BaseClient:

    @abstractmethod
    async def send_request(self,
                           url: str,
                           method: str,
                           body: str | bytearray | bytes = '',
                           path_parameters: Iterable[Iterable[str]] | None = None,
                           headers: None | dict = None,
                           json: str = '') -> Response:
        raise NotImplementedError

    async def get(self, url, body='', headers=None, json='', path_parameters=None) -> Response:
        return await self.send_request(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters
        )

    async def post(self, url, body='', headers=None, json='', path_parameters=None) -> Response:
        return await self.send_request(
            url=url,
            method="POST",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters
        )

    async def options(self, url, body='', headers=None, json='', path_parameters=None) -> Response:
        return await self.send_request(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters
        )


    async def head(self, url, body='', headers=None, json='', path_parameters=None) -> Response:
        return await self.send_request(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters
        )

    async def put(self, url, body='', headers=None, json='', path_parameters=None) -> Response:
        return await self.send_request(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters
        )

    async def delete(self, url, body='', headers=None, json='', path_parameters=None) -> Response:
        return await self.send_request(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters
        )

    async def trace(self, url, body='', headers=None, json='', path_parameters=None) -> Response:
        return await self.send_request(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters
        )


    async def connect(self, url, body='', headers=None, json='', path_parameters=None) -> Response:
        return await self.send_request(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters
        )

    async def patch(self, url, body='', headers=None, json='', path_parameters=None) -> Response:
        return await self.send_request(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters
        )


    async def link(self, url, body='', headers=None, json='', path_parameters=None) -> Response:
        return await self.send_request(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters
        )

    async def unlink(self, url, body='', headers=None, json='', path_parameters=None) -> Response:
        return await self.send_request(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters
        )


class Client(BaseClient):
    """
    Session like class Client

    Client used to send requests with same headers or
    send requests using same connections which are stored in
    the Client's connection pool
    """

    def __init__(self, headers=None):
        """
        Initalization method for Client, session like object

        :param headers: HTTP headers that should be sent with each request in this session
        """

        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'text/html',
                'Accept-Language': 'en-us',
                'Accept-Charser': 'ISO-8859-1,utf-8',
                'Connection': 'keep-alive'
            }
        self.connection_mapper = {}
        self.headers = headers

    async def send_request(self,
                           url: str,
                           method: str,
                           body: str | bytearray | bytes = '',
                           path_parameters: Iterable[Iterable[str]] | None = None,
                           headers: None | dict = None,
                           json: str = '') -> Response:
        """
        Simulates http request

        :param url: Url where should be request send
        :param headers: Http headers which should be used in this GET request
        :param body: Http body part
        :param method: Http message mthod
        :param path_parameters:
        :returns: Response object which represents returned by server response
        """

        if headers is None:
            headers = {}
        splited_url = UrlParser.parse(url)
        transport, protocol = await self.make_connection(splited_url)

        json = _json.dumps(json)
        request = Request(
            method=method,
            host=splited_url.get_url_without_path(),
            headers=self.headers | headers,
            path=splited_url.path,
            path_parameters=path_parameters,
            json=json,
            body=body
        )
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        protocol.send_http_request(request, future)
        raw_response = await future

        if isinstance(raw_response, Exception):
            raise raw_response
        response = ResponseParser.parse(raw_response)
        response.request = request
        return response

    async def make_connection(self, splited_url):
        """
        Getting connection from already opened connections, to perform Keep-Alive logic,
        if these connections exists or create the new one and save into connection pool

        :param splited_url: Url object which contains all url parts
        (scheme, version, subdomain, domain, ...)
        :returns: (transport, protocol) which are objects returned by loop.create_connection method
        """

        transport, protocol = self.connection_mapper.get(
            splited_url.get_url_for_dns(), (None, None))

        if transport and transport.is_closing():
            transport, protocol = None, None

        if not transport:
            ip, port = resolve_domain(splited_url.get_url_for_dns())
            loop = asyncio.get_event_loop()
            connection_coroutine = loop.create_connection(
                lambda: HttpClientProtocol(),
                host=ip,
                port=port
            )
            try:
                transport, protocol = await asyncio.wait_for(connection_coroutine,
                                                             timeout=DEFAULT_CONNECTION_TIMEOUT)
            except asyncio.exceptions.TimeoutError as err:
                raise Exception('Timeout Error') from err

            self.connection_mapper[splited_url.get_url_for_dns(
            )] = transport, protocol
        else:
            log.info("Using previous connection")
        return transport, protocol

    async def __aenter__(self):
        """
        Implements startpoint for Client
        for keyword <with> supporting

        :returns: Client object
        """
        return self

    async def __aexit__(self, *args, **kwargs):
        """
        Closes session resources which are all transport
        connections into connection pool
        """

        for host, (transport, protocol) in self.connection_mapper.items():
            transport.close()
            log.info(f"Transport closed {transport=}")
