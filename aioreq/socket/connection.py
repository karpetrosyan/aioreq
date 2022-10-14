import asyncio
import logging
import re
import socket
from functools import lru_cache, partial

from dns import resolver
from dns.resolver import NXDOMAIN

from ..errors.requests import AsyncRequestsError
from ..errors.requests import InvalidDomainName
from ..errors.response import ClosedConnectionWithoutResponse
from ..parser.response_parser import ResponseParser
from ..parser.url_parser import UrlParser
from ..settings import DEFAULT_DNS_SERVER, LOGGER_NAME
from .buffer import Buffer, HttpBuffer

resolver = resolver.Resolver()
resolver.nameservers = [DEFAULT_DNS_SERVER]

log = logging.getLogger(LOGGER_NAME)


@lru_cache
def resolve_domain(hostname) -> tuple[str, int]:
    """
    Ip port resolving by making dns requests

    :param hostname: Domain name for example youtube.com
    :returns: ip and port for that domain
    :rtype: [str, int]
    """

    try:
        resolved_data = resolver.resolve(hostname)
        for ip in resolved_data:
            result = (ip.address, 80)
            break
    except NXDOMAIN as e:
        try:
            result = socket.gethostbyname(hostname), 80
            return result 
        except:
            ...
        raise InvalidDomainName from e
    return result


class HttpClientProtocol(asyncio.Protocol):
    """
    Default HTTP client connection implementation including keep alive connection
    for HTTP/1.1
    Used for sending asynchronus request via one socket, if many requests via the same socket
    needed then use PiplineHttpClientProtocol
    Pipeline works for HTTP/1.1
    """


    def __init__(self):
        """
        Initalization method for HttpClientProtocol which implements low level socket programming
        """

        self.buffer = HttpBuffer()
        self.future = None
        self.decoded_data = ''
        self.message_pending = False
        self.expected_length = None
        self.buffer_callbacks = 0

    def clean_communication(self):
        self.message_pending = False
        self.expected_length = None
        self.decoded_data = ''
        self.future = None
        self.buffer_callbacks = 0

    def verify_response(self):
        """
        Response verifying called when response with specified self.expected_length
        got from the transport.
        It's should reset all response getting attributes and also set result for response waiting future

        :returns: None
        """

        log.debug(f"Verify message {self.decoded_data=} | {self.expected_length=}")
        try:
            self.future.set_result(self.decoded_data)
        except asyncio.exceptions.InvalidStateError as err:
            log.exception(f"{self.future=} | Result : {self.future.result()}")
        self.clean_communication()

    def check_buffer(self, future):
        """
        check_buffer calls whenever bytes added to the application buffer
        using add_bytes or left_add_bytes coroutines,
        checking if message containser Content-Length then receive message with
        the expected lenth otherwise use chunked messaging

        :param future: future which called this method after finishing
        :returns: None
        """
        if future:
            self.buffer_callbacks -= 1

        loop = asyncio.get_event_loop()
        if not self.message_pending:
            self.decoded_data += self.buffer.get_data()
            length = ResponseParser.search_content_length(self.decoded_data)
            self.expected_length = length
            if not length:
                log.debug(f"Length not found in {self.decoded_data=}")
            else:
                self.message_pending = True
                without_body_length = ResponseParser.get_without_body_length(self.decoded_data)
                tail = self.decoded_data[without_body_length:]
                left_add_bytes_task = loop.create_task(
                        self.buffer.left_add_bytes(bytearray(
                            tail, 'utf-8'
                            ))
                        )
                left_add_bytes_task.add_done_callback(self.check_buffer)
                self.buffer_callbacks += 1
                self.decoded_data = self.decoded_data[:without_body_length]
        else:
            if self.buffer.current_point >= self.expected_length:
                body_data = self.buffer.get_data(self.expected_length)
                self.decoded_data +=  body_data
                return self.verify_response()

        if (not self.buffer_callbacks) and self.transport.is_closing():
            # if not processing data and transport is closed then raise an exception
            print(self.future)
            self.future.set_result(ClosedConnectionWithoutResponse())
            

    def connection_made(self, transport):
        """
        asyncio.Protocol callback which calls whenever conntection successfully made

        :param transport: transport object which gives us asyncio library
        :returns: None
        """
        
        self.transport = transport


    def data_received(self, data):
        """
        asycnio.Protocol callback which calls whenever transport receive bytes

        :param data: received bytes
        """

        log.info('Data received: {!r}'.format(data))
        loop = asyncio.get_event_loop()
        add_buffer_task = loop.create_task(self.buffer.add_bytes(data))
        add_buffer_task.add_done_callback(self.check_buffer)
        self.buffer_callbacks += 1
        
    def connection_lost(self, exc):
        """
        asyncio.Protocol callback which calls whenever server closed the connection

        :param exc: Exception which is connection closing reason
        :returns: None
        """


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
        
        raw_text = request.get_raw_request()
        if self.future is not None:
            raise AsyncRequestsError(f"Trying to use async requests via the same connection using unsupported for that version")

        self.future = future
        log.info(f"Sending http request \n{raw_text}")

        request.raw_request = raw_text 
        self.transport.write(raw_text)

class PiplineHttpClientProtocol(HttpClientProtocol):
    ...
