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
from ..settings import DEFAULT_DNS_SERVER
from dns import resolver
from dns.resolver import NXDOMAIN
from functools import partial

resolver = resolver.Resolver()
resolver.nameservers = [DEFAULT_DNS_SERVER]

log = logging.getLogger(LOGGER_NAME)

@lru_cache
def resolve_domain(hostname) -> tuple[str, int]:
    """
    Ip port resolving by making dns requests

    :param hostname: Domain name for example youtube.com
    """

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
        """
        Initalization method for HttpClientProtocol which implements low level socket programming
        """

        self.buffer = HttpBuffer()
        self.future = None
        self.decoded_data = ''
        self.message_pending = False
        self.expected_length = None

    def verify_response(self):
        """
        Response verifying called when response with specified self.expected_length
        got from the transport.
        It's should reset all response getting attributes and also set result for response waiting future

        :returns: None
        """

        log.debug(f"Verify message {self.decoded_data=} | {self.expected_length=}")
        self.future.set_result(self.decoded_data)
        self.message_pending = False
        self.expected_length = None
        self.decoded_data = ''

    def check_buffer(self, future):
        """
        check_buffer calls whenever bytes added to the application buffer
        using add_bytes or left_add_bytes coroutines,
        checking if message containser Content-Length then receive message with
        the expected lenth otherwise use chunked messaging

        :param future: future which called this method after finishing
        :returns: None
        """

        loop = asyncio.get_event_loop()
        if not self.message_pending:
            log.debug(self.buffer)
            log.debug(future)
            self.decoded_data += self.buffer.get_data()
            length = ResponseParser.search_content_length(self.decoded_data)
            self.expected_length = length
            if not length:
                log.debug(f"Length not found in {self.decoded_data=}")
                return
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
        """
        asyncio.Protocol callback which calls whenever conntection successfully made

        :param transport: transport object which gives us asyncio library
        :returns: None
        """
        
        log.debug(f"Connected to : {transport=}")
        self.transport = transport

    def data_received(self, data):
        """
        asycnio.Protocol callback which calls whenever transport receive bytes

        :param data: received bytes
        """

        log.debug('Data received: {!r}'.format(data))
        loop = asyncio.get_event_loop()
        add_buffer_task = loop.create_task(self.buffer.add_bytes(data))
        add_buffer_task.add_done_callback(self.check_buffer)
        
    def connection_lost(self, exc):
        """
        asyncio.Protocol callback which calls whenever server closed the connection

        :param exc: Exception which is connection closing reason
        :returns: None
        """

        self.future.set_result(exc)

    def send_http_request(self, request: 'Request', future):
        """
        writes request raw message type of bytearray into transport,
        low level http send function which simulates socket.sendall under the hood

        :param request: Request object which can give us bytearray representation which contains
        all the headers, method, scheme and version data
        :param future: future awaiting by async client, which result changes in the connection_lost or
        verify_response methods
        :returns: None
        """

        self.future = future
        log.debug(f"Sending http request \n{request.get_raw_request()}")
        self.transport.write(request.get_raw_request())
        log.debug(f"Sent")

