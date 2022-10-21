import logging
import asyncio
import json as _json

from abc import ABCMeta
from abc import abstractmethod
from collections.abc import Collection
from ..parser.url_parser import UrlParser
from ..parser.response_parser import ResponseParser
from ..parser import request_parser
from ..socket.connection import resolve_domain
from ..socket.connection import HttpClientProtocol
from ..settings import LOGGER_NAME
from ..settings import DEFAULT_CONNECTION_TIMEOUT
from ..socket.buffer import HttpBuffer
from ..protocol.headers import Header
from typing import Iterable
from enum import Enum

log = logging.getLogger(LOGGER_NAME)

class BodyReceiveStrategies(Enum):
    """
    Enumeration which implements Strategy design pattern, used to
    choose a way of parsing response
    """
    chunked = 'chunked'
    content_length = 'content_length'

    def parse_content_length(self, pending_message) -> None | str:
        """
        Parse incoming PendingMessage object which receiving data which body length
        specified by Content-Length header.

        RFC[2616] 14.13 Content-Length:
            The Content-Lenght entity-header field indicates the size of the entity-body,
            in decimal number of OCTETs, sent to the recipent or, in the case of the HEAD method,
            the size of the entity-body that would have been sent had the request been a GET.

        :param pending_message: PendingMessage instance representing message receiving
        :return: None or the verified string which seems like an HTTP message 
        """
                                                                                

        if len(pending_message.text) >= pending_message.content_length:
            pending_message.switch_data(pending_message.content_length)
            return pending_message.message_verify()

    def parse_chunked(self, pending_message) -> None | str:
        """
        Parse incoming PendingMessage object which receiving data which body length
        specified by Transfer-Encoding : chunked.

        RFC[2616] 3.6.1 Chunked Transfer Coding:
            The chunked encoding modifies the body of a message in order to transfer it as a series of
            chunkd, each with its own size indicator, followed by an OPTIONAL trailer containing entity-header
            fields. This allows dynamically produced content to be transferred along with the information
            necessary for the recipient to verify that it has received the full message.

        :param pending_message: PendingMessage instance representing message receiving
        :return: None or the verified string which seems like an HTTP message 
        """

        while True:
            log.info(f'Parsing by chunks {repr(pending_message.text)=}')

            if pending_message.bytes_should_receive_and_save:
                if pending_message.bytes_should_receive_and_save <= len(pending_message.text):
                    pending_message.switch_data(pending_message.bytes_should_receive_and_save)
                    pending_message.bytes_should_receive_and_save = 0
                    pending_message.bytes_should_receive_and_ignore = 2
            elif pending_message.bytes_should_receive_and_ignore:
                if pending_message.bytes_should_receive_and_ignore <= len(pending_message.text):
                    pending_message.ignore_data(pending_message.bytes_should_receive_and_ignore) 
                    pending_message.bytes_should_receive_and_ignore = 0
            else:
                for pattern in ResponseParser.regex_end_chunks:
                    end_match = pattern.search(pending_message.text)
                    if end_match:
                        log.info(f"{end_match=}")
                        return pending_message.message_verify()

                match = ResponseParser.regex_find_chunk.search(pending_message.text)
                log.info(f"{match=}")
                if match is None:
                    return
                size = int(match.group('content_size'))
                pending_message.bytes_should_receive_and_save = size
                log.info(f"{pending_message.bytes_should_receive_and_save=}")
                pending_message.ignore_data(match.end() - match.start())

    def parse(self, pending_message) -> str | None:
        """
        General interface to work with parsing strategies

        :param pending_message: object which is working with message pending
        :returns: Parsed and verifyed http response or NoneType object
        :rtype: str or None
        """

        match self.value:
            case 'content_length':
                return self.parse_content_length(pending_message)
            case 'chunked':
                return self.parse_chunked(pending_message)

class PendingMessage:
    """
    Implementing message receiving using BodyReceiveStrategies which support
    receiving by content_length or chunked
    """

    def __init__(self,
                 text: str) -> None:
        self.text = text
        self.__headers_done: bool = False
        self.body_receiving_strategy: BodyReceiveStrategies | None = None
        self.content_length: int | None = None
        self.bytes_should_receive_and_save: int = 0 
        self.bytes_should_receive_and_ignore: int = 0
        self.message_data : str = ''

    def switch_data(self, length: int) -> None:
        """
        Delete data from the self.text and add into self.message_data

        :param length: Message length to delete from the self.text
        :return: None
        """

        log.info(f"Switching data with length : {length}")
        self.message_data += self.text[:length]
        self.text = self.text[length:]

    def message_verify(self) -> None:
        """
        If message seems like full, call this method to return and clean the
        self.message_data

        :returns: None
        """

        msg = self.message_data
        self.message_data = ''
        return msg

    def ignore_data(self, length: int) -> None:
        """
        Just delete text from self.text by giving length

        :param length: Length message which should be ignored (deleted)
        :returns: None
        """

        log.info(f"Ignoring {repr(self.text[:length])}")
        self.text = self.text[length:]

    def headers_done(self) -> bool:
        """
        Check if text contains HTTP message data included full headers
        or there is headers coming now
        """

        if not self.__headers_done:
            is_done = ResponseParser.headers_done(self.text)
            log.info(f"{is_done=}")
            if is_done:
                without_body_len = ResponseParser.get_without_body_length(self.text)
                self.switch_data(without_body_len)
            self.__headers_done = is_done
        return self.__headers_done


    def find_strategy(self) -> None:
        """
        Find and set strategy for getting message, it can be chunked receiving or
        with content_length

        :returns: None
        """

        content_length = ResponseParser.search_content_length(self.message_data)
        if content_length is not None:
            self.content_length = content_length
            self.body_receiving_strategy = BodyReceiveStrategies.content_length
        else:
            self.body_receiving_strategy = BodyReceiveStrategies.chunked

    def add_data(self, text: str) -> None | str:
        """
        Calls whenever new data required to be added
    
        :param text: Text to add
        :ptype text: str

        :returns: None if message not verified else verified message
        """

        log.info(f"Got {text=}")
        self.text += text

        if self.headers_done():
             
            if not self.body_receiving_strategy:
                self.find_strategy()
                
            result = self.body_receiving_strategy.parse(self) 
            if result is not None:
                return result


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
            json: str = '',
            path_parameters: Iterable[Iterable[str]] | None = None,
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
                           path_parameters: Iterable[Iterable[str]] | None = None,
                           headers: None | dict = None,
                           json: str = '') -> Response:...
    async def get(
            self, 
            url : str, 
            body : str | bytearray | bytes= '', 
            headers : None | dict[str, str] = None, 
            json: dict | None = None, 
            path_parameters: None | Iterable[Collection[str, str]] = None, 
            obj_headers = Iterable[Header]) -> Response: ...


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
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
        self.connection_mapper = {}
        self.headers = headers

    async def get(
             self, 
             url : str, 
             body : str | bytearray | bytes= '', 
             headers : None | dict[str, str] = None, 
             json: dict | None = None, 
             path_parameters: None | Iterable[Collection[str, str]] = None, 
             obj_headers = Iterable[Header]) -> Response:
        return await self.send_request(
            url=url,
            method="GET",
            body=body,
            headers=headers,
            json=json,
            path_parameters=path_parameters,
            obj_headers=obj_headers
        )

    async def send_request(self,
                           url: str,
                           method: str,
                           body: str | bytearray | bytes = '',
                           path_parameters: Iterable[Iterable[str]] | None = None,
                           headers: None | dict[str, str] = None,
                           json: dict | None = None,
                           obj_headers: Iterable[Header] = None) -> Response:
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
