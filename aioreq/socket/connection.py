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


@lru_cache # cache already requested domains
def resolve_domain(hostname: str) -> tuple[str, int]:
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
    needed, then use PiplineHttpClientProtocol
    Pipeline works for HTTP/1.1
    """

    def __init__(self) -> None:
        """
        Initalization method for HttpClientProtocol which implements low level socket programming
        """
        from ..protocol.http import PendingMessage

        self.future: None | asyncio.Future = None
        self.pending_message: PendingMessage = PendingMessage(text='') 

    def clean_communication(self) -> None:
        """
        Cleaning communication variables to re-use the connection
        """
        self.future = None

    def verify_response(self, raw_data) -> None:
        """
        Response verifying called when response with specified self.expected_length
        got from the transport.
        It's should reset all response getting attributes and also set result for response waiting future

        :returns: None
        """

        log.debug(
            f"Verify message {raw_data=} | {raw_data=}")
        try:
            self.future.set_result(raw_data)
        except asyncio.exceptions.InvalidStateError as err:
            log.exception(f"{self.future=} | Result : {self.future.result()}")
        self.clean_communication()

    def connection_made(self, transport : asyncio.BaseTransport) -> None:
        """
        asyncio.Protocol callback which calls whenever conntection successfully made

        :param transport: transport object which gives us asyncio library
        :returns: None
        """

        self.transport = transport

    def data_received(self, data: bytes) -> None:
        """
        asycnio.Protocol callback which calls whenever transport receive bytes

        :param data: received bytes
        """
        decoded_data = data.decode()
        resp = self.pending_message.add_data(decoded_data)
        if resp is not None:
            return self.verify_response(resp)


    def connection_lost(self, exc: None | Exception) -> None:
        """
        asyncio.Protocol callback which calls whenever server closed the connection

        :param exc: Exception which is connection closing reason
        :returns: None
        """

    def send_http_request(self, request: 'Request',
                          future : asyncio.Future) -> None:
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
            raise AsyncRequestsError(
                f"Trying to use async requests via the same connection using unsupported for that version")

        self.future = future

        request.raw_request = raw_text
        self.transport.write(raw_text)


class PiplineHttpClientProtocol(HttpClientProtocol):
    ...
