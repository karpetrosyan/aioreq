import re
import socket
import logging
import asyncio

from ..parser.url_parser import UrlParser
from ..settings import LOGGER_NAME
from dns import resolver
from functools import partial

resolver = resolver.Resolver()
resolver.nameservers = ['8.8.8.8']

log = logging.getLogger(LOGGER_NAME)

def resolve_domain(hostname):
    try:
        resolved_data = resolver.resolve(hostname)

        for ip in resolved_data:
            result = (ip.address, resolved_data.port)
            log.debug(f'Resolved {hostname=} got {result}')
            return result
    except:
        return (socket.gethostbyname(hostname), 80)

class Request:

    @classmethod
    async def create(cls, method, host, headers, path):
        self         = cls()
        self.host    = host
        self.headers = {}
        self.method  = method
        self.path    = path
        return self

    def __str__(self):
        return '\r\n'.join((
                f'{self.method} {self.path} HTTP/1.1',
                f'Host: {self.host}',
                *(f"{key}:  {value}" for key, value in self.headers.items())
                )) + '\r\n\r\n'


class HttpClientProtocol(asyncio.Protocol):

    def __init__(self):
        self.buffer = ''

    def connection_made(self, transport):
        log.debug(f"Connected to : {transport=}")
        self.transport = transport

    def data_received(self, data):
        log.debug(f"received : {data=}")
        deocded_data = data.decode()
        log.debug('Data received: {!r}'.format(decoded_data))
        self.buffer += decoded_data

    def connection_lost(self, exc):
        log.debug('The server closed the connection')

    def send_http_request(self, request: Request):
        log.debug(f"Sending http request \n{str(request)}")
        self.transport.write(str(request).encode())
        log.debug(f"data sent")
        return True

class Client:

    def __init__(self):
        self.connection_mapper = {}
        self.headers = {}

    async def get(self, url, *args):
        splited_url = UrlParser.parse(url)
        transport, protocol = await self.make_connection(splited_url)
        print(splited_url)
        request = await Request.create(
                method = "GET",
                host = splited_url.get_url_without_path(),
                headers = self.headers,
                path = splited_url.path
                )
        protocol.send_http_request(request)
         

    async def make_connection(self, splited_url):
        transport = self.connection_mapper.get(splited_url.get_url_for_dns(), None)
        if not transport:
            ip, port = resolve_domain(splited_url.get_url_for_dns())
            loop = asyncio.get_event_loop()
            connection_coroutine = loop.create_connection(
                    lambda: HttpClientProtocol(),
                    host=ip,
                    port=port
                        )
            transport, protocol = await asyncio.wait_for(connection_coroutine, timeout=3)
            self.connection_mapper[splited_url.get_url_for_dns()] = transport
        return transport, protocol
    

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        for host, transport in self.connection_mapper.items():
            transport.close()
