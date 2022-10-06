import re
import socket
import logging
import asyncio

from .buffer import Buffer
from ..protocol.messages import Request
from ..protocol.messages import Response
from ..parser.url_parser import UrlParser
from ..parser.response_parser import ResponseParser
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
        self.decoded_data = ''
        self.message_pending = False
        self.expected_length = None

    def verify_response(self):
        log.debug(f"Verify message {self.decoded_data=} | {self.expected_length=}")
        self.future.set_result(self.decoded_data)
        self.message_pending = False
        self.expected_length = None
        self.decoded_data = ''

    def check_buffer(self, future):
        loop = asyncio.get_event_loop()
        if not self.message_pending:
            log.debug(self.buffer)
            log.debug(future)
            self.decoded_data += self.buffer.get_data()
            length = ResponseParser.search_content_length(self.decoded_data)
            self.expected_length = length
            if not length:
                log.debug(f"Length not found in {self.decoded_data=}")
                return False
            log.debug(f"Length found in {self.decoded_data=}")
            self.message_pending = True
            without_body_length = ResponseParser.get_without_body_length(self.decoded_data)
            log.debug(f"From {self.decoded_data=} {without_body_length=}")
            tail = self.decoded_data[without_body_length:]
            log.debug(f"Got {tail=} from {self.decoded_data}")
            left_add_bytes_task = loop.create_task(
                    self.buffer.left_add_bytes(bytearray(
                        tail, 'utf-8'
                        ))
                    )
            left_add_bytes_task.add_done_callback(self.check_buffer)
            self.decoded_data = self.decoded_data[:without_body_length]
        else:
            if self.buffer.current_point == self.expected_length:
                body_data = self.buffer.get_data()
                self.decoded_data +=  body_data
                self.verify_response()



    def connection_made(self, transport):
        log.debug(f"Connected to : {transport=}")
        self.transport = transport

    def data_received(self, data):
        log.debug('Data received: {!r}'.format(data))
        loop = asyncio.get_event_loop()
        add_buffer_task = loop.create_task(self.buffer.add_bytes(data))
        add_buffer_task.add_done_callback(self.check_buffer)
        

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
        raw_response = await future
        return ResponseParser.parse(raw_response)
         

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
