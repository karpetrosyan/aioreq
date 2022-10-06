import re
import socket
import logging
import asyncio

from functools import lru_cache
from .buffer import Buffer
from .buffer import HttpBuffer
from ..parser.url_parser import UrlParser
from ..parser.response_parser import ResponseParser
from ..settings import LOGGER_NAME
from dns import resolver
from dns.resolver import NXDOMAIN
from functools import partial

resolver = resolver.Resolver()
resolver.nameservers = ['8.8.8.8']

log = logging.getLogger(LOGGER_NAME)

@lru_cache
def resolve_domain(hostname) -> tuple[str, int]:
    try:
        resolved_data = resolver.resolve(hostname)
        for ip in resolved_data:
            result = (ip.address, 80)
            log.debug(f'Resolved {hostname=} got {result}')
            break
    except NXDOMAIN as e:
        log.debug(
                f"Can't resolve {hostname=} via "
                f"{resolver.nameservers=} trying localhost domains"
                )
        result = socket.gethostbyname(hostname), 80
    return result


class HttpClientProtocol(asyncio.Protocol):

    def __init__(self):
        self.buffer = HttpBuffer()
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
        ...

    def send_http_request(self, request: 'Request', future):
        self.future = future
        log.debug(f"Sending http request \n{request.get_raw_request()}")
        self.transport.write(request.get_raw_request())
        log.debug(f"Sent")
        return True

