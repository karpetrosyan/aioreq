import re
import socket
import logging
import asyncio

from .buffer import Buffer
from ..protocol.messages import Request
from ..protocol.messages import Response
from ..parser.url_parser import UrlParser
from ..settings import LOGGER_NAME
from dns import resolver
from dns.resolver import NXDOMAIN
from functools import partial

resolver = resolver.Resolver()
resolver.nameservers = ['8.8.8.8']

log = logging.getLogger(LOGGER_NAME)

def resolve_domain(hostname) -> tuple[str, int]:
    try:
        resolved_data = resolver.resolve(hostname)
        for ip in resolved_data:
            result = (ip.address, resolved_data.port)
            log.debug(f'Resolved {hostname=} got {result}')
    except NXDOMAIN as e:
        log.debug(
                f"Can't resolve {hostname=} via "
                f"{resolver.nameservers=} trying localhost domains"
                )
        result = socket.gethostbyname(hostname), 80
    return result


class HttpClientProtocol(asyncio.Protocol):

    def __init__(self):
        self.buffer = Buffer()
        self.future = None

    def verify_response(self):
        self.future.set_result(True)

    def check_buffer(self):
        print(self.buffer)
        self.verify_response()

    def connection_made(self, transport):
        log.debug(f"Connected to : {transport=}")
        self.transport = transport

    def data_received(self, data):
        log.debug('Data received: {!r}'.format(data))
        loop = asyncio.get_event_loop()
        loop.create_task(self.buffer.add_bytes(data))

    def connection_lost(self, exc):
        log.debug('The server closed the connection')

    def send_http_request(self, request: Request, future):
        self.future = future
        log.debug(f"Sending http request \n{str(request)}")
        self.transport.write(str(request).encode())
        return True

class Client:

    def __init__(self):
        self.connection_mapper = {}
        self.headers = {}

    async def get(self, url, *args):
        splited_url = UrlParser.parse(url)
        transport, protocol = await self.make_connection(splited_url)
        request = await Request.create(
                method = "GET",
                host = splited_url.get_url_without_path(),
                headers = self.headers,
                path = splited_url.path
                )
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        protocol.send_http_request(request, future)
        response = await future
        return response
         

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
            log.info(f"Transport closed {transport=}")
