import re
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
    resolved_data = resolver.resolve(hostname)

    for ip in resolved_data:
        result = (ip.address, resolved_data.port)
        log.debug(f'Resolved {hostname=} got {result}')
        return result

class HttpClientProtocol(asyncio.Protocol):

    def __init__(self):
        ...

    def connection_made(self, transport):
        return 
        data = (
                f"GET /user/me HTTP/1.1\r\n"
                f"Host:192.168.0.185:8000\r\n\r\n"
                )
        transport.write(data.encode())

    def data_received(self, data):
        print('Data received: {!r}'.format(data.decode()))

    def connection_lost(self, exc):
        print('The server closed the connection')


class Request:

    @classmethod
    async def create(cls, method, host, headers, path):
        self         = cls()
        self.host    = host
        self.headers = {}
        self.method  = method
        self.path    = path


    def __str__(self):
        return (
                f'{self.method} '
                )

class Client:

    def __init__(self):
        self.connection_mapper = {}
        self.headers = {}

    async def get(self, url, *args):
        splited_url = UrlParser.parse(url)
        request = await Request.create(
                method = "GET",
                host = splited_url.get_url_without_path,
                headers = self.headers,
                path = splited_url.path
                )
        transport = await self.make_connection(splited_url)
         

    async def make_connection(self, splited_url):
        transport = self.connection_mapper.get(splited_url.get_url_for_dns(), None)
        if not transport:
            ip, port = resolve_domain(splited_url.get_url_for_dns())
            ip = '192.168.0.185'
            port = 8000
            loop = asyncio.get_event_loop()
            connection_coroutine = loop.create_connection(
                    lambda: HttpClientProtocol(),
                    host=ip,
                    port=port
                        )
            transport, protocol = await asyncio.wait_for(connection_coroutine, timeout=3)
            self.connection_mapper[splited_url.get_url_for_dns()] = transport
        return transport
    

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        for host, transport in self.connection_mapper.items():
            transport.close()
