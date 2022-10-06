import asyncio
import logging

from ..parser.url_parser import UrlParser
from ..parser.response_parser import ResponseParser
from ..socket.connection import resolve_domain
from ..socket.connection import HttpClientProtocol
from ..settings import LOGGER_NAME
from ..settings import DEFAULT_CONNECTION_TIMEOUT

log = logging.getLogger(LOGGER_NAME)

class Response:

    def __init__(
            self,
            scheme_and_version : str,
            status : int,
            status_message : str,
            headers : dict,
            body : str,
            request : 'Request' = None):
        """
        Response initalization method

        :param scheme_and_version: Version and scheme for http. For example HTTP/1.1
        :param status: response code returned with response
        :param status_message: message returned with response status code
        :param headers: response headers for example, Connection : Keep-Alive if version lower than HTTP/1.1
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

class Request:

    def __init__(
            self, 
            method, 
            host, 
            headers, 
            path, 
            scheme_and_version = 'HTTP/1.1'
            ) -> 'Request':
        """
        Request initalization method

        :param method: HTTP method (GET, POST, PUT, PATCH)
        :param host: HTTP header host which contains host's domain
        :param headers: HTTP headers
        :param path: HTTP server endpoint path specified after top-level domain
        :scheme_and_version: HTTP scheme and version where HTTP is scheme 1.1 is a version
        :returns: None
        """
        self.host    = host
        self.headers = headers
        self.method  = method
        self.path    = path
        self.scheme_and_version = scheme_and_version

    def get_raw_request(self) -> str:
        """
        Bytearray to write in the transport

        :returns: raw http request text type of bytearray
        """
        return ('\r\n'.join((
                f'{self.method} {self.path} {self.scheme_and_version}',
                f'Host:   {self.host}',
                *(f"{key}:  {value}" for key, value in self.headers.items())
                )) + '\r\n\r\n').encode('utf-8')

    def __repr__(self) -> str:
        return '\n'.join((
                f"Request(",
                f"\tscheme_and_version='{self.scheme_and_version}'",
                f"\thost= '{self.host}'",
                f"\tmethod= '{self.method}'",
                f"\tpath= '{self.path}'",
                f"\tHeaders:",
                *(
                    f"\t\t{key}: {value}" for key, value in self.headers.items()
                    ),
                ')'
                ))

class Client:

    def __init__(self, headers = {}):
        """
        Initalization method for Client, session like object

        :param headers: HTTP headers that should be send with each request in this session
        """

        self.connection_mapper = {}
        self.headers = headers

    async def get(self, url, headers = {}) -> Response:
        """
        Simulates http GET method

        :param url: Url where should be request send
        :param headers: Http headers which should be used in this GET request
        :returns: Response object which represents returned by server response 
        """

        splited_url = UrlParser.parse(url)
        transport, protocol = await self.make_connection(splited_url)
        request = Request(
                method = "GET",
                host = splited_url.get_url_without_path(),
                headers = self.headers | headers,
                path = splited_url.path,
                )
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        protocol.send_http_request(request, future)
        raw_response = await future
        response = ResponseParser.parse(raw_response)
        response.request = request
        return response
         

    async def make_connection(self, splited_url):
        """
        Getting connection from already opened connections, to perform Keep-Alive logic,
        if these connections exists or create the new one and save into connection pool

        :param splited_url: Url object which contains all url parts (scheme, version, subdomain, domain, ...)
        :returns: (transport, protocol) which are objects returned by loop.create_connection method
        """

        transport, protocol = self.connection_mapper.get(splited_url.get_url_for_dns(), (None, None))

        if transport and transport.is_closing():
            log.debug(f"Remake connection")
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
                transport, protocol = await asyncio.wait_for(connection_coroutine, timeout=DEFAULT_CONNECTION_TIMEOUT)
            except asyncio.exceptions.TimeoutError as err:
                raise Exception('Timeout Error') from err

            self.connection_mapper[splited_url.get_url_for_dns()] = transport, protocol
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
