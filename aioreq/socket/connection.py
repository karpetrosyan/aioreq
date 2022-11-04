import asyncio
import logging
import re
import socket

from functools import lru_cache 
from functools import partial

from ..errors.requests import AsyncRequestsError
from ..errors.requests import InvalidDomainName
from ..errors.response import ClosedConnectionWithoutResponse
from ..errors.response import InvalidResponseData

from ..parser.response_parser import ResponseParser
from ..parser.url_parser import UrlParser
from ..settings import DEFAULT_DNS_SERVER, LOGGER_NAME
from .buffer import Buffer, HttpBuffer

from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger(LOGGER_NAME)

executor = ThreadPoolExecutor(2)

async def resolve_domain(hostname: str,
                         memo = {}) -> tuple[str, int]:
    """
    Ip port resolving by making dns requests

    :param hostname: Domain name for example youtube.com
    :returns: ip and port for that domain
    :rtype: [str, int]
    """
    if hostname in memo:
        result = memo[hostname]
        if isinstance(result, asyncio.Future): # task pending
            return await result

    log.debug(f"trying resolve {hostname=}")
    loop = asyncio.get_event_loop()
    fut = loop.run_in_executor(executor, lambda: socket.gethostbyname(hostname))
    memo[hostname] = fut 
    host = await fut
    memo[hostname] = host
    return host


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

        try:
            self.future.set_result(raw_data) # type: ignore
        except asyncio.exceptions.InvalidStateError as err:
            log.debug("Trying to set result for the future which is already done")
        self.clean_communication()

    def connection_made(self, transport) -> None:
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
        try:
            resp = self.pending_message.add_data(data)
        except UnicodeDecodeError as e:
            if not self.future.done():
                self.future.set_exception(InvalidResponseData('Can\'t understand server response')) 
            self.transport.close()
            return
        else:
            if resp is not None:
                return self.verify_response(resp)


    def connection_lost(self, exc: None | Exception) -> None:
        """
        asyncio.Protocol callback which calls whenever server closed the connection

        :param exc: Exception which is connection closing reason
        :returns: None
        """

    def send_http_request(self, request: 'Request', # type: ignore
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
            log.critical(
                    f"Async requests error was raised!"
                    )
            raise AsyncRequestsError(
                f"Trying to use async requests via the same connection using unsupported for that version")

        self.future = future

        request.raw_request = raw_text
        log.debug(f'Writing text: {raw_text}')
        self.transport.write(raw_text)
