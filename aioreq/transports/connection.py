import asyncio
import logging
import ssl
from typing import Tuple

import certifi
from dns import asyncresolver

from .buffer import Buffer, StreamBuffer
from ..errors.requests import AsyncRequestsError
from ..settings import LOGGER_NAME

res = asyncresolver.Resolver()
res.nameservers = ['1.1.1.1', '8.8.8.8']

log = logging.getLogger(LOGGER_NAME)

context = ssl.SSLContext(ssl.PROTOCOL_TLS)
context.load_verify_locations(certifi.where())


async def get_address(host):
    answers = await res.resolve(host)
    return answers.rrset[0].address


dns_cache = dict()


async def resolve_domain(
        hostname: str,
) -> str:
    """
    Makes an asynchronous DNS request to resolve the IP address
    :param hostname: Domain name for example YouTube.com
    :type hostname: str
    :returns: ip and port for that domain
    :rtype: [str, int]
    """
    if hostname in dns_cache:
        if not isinstance(dns_cache[hostname], str):
            log.debug('Got cached dns query')
            return await dns_cache[hostname]
        return dns_cache[hostname]

    log.debug(f"trying resolve {hostname=}")
    coro = asyncio.create_task(get_address(hostname))
    dns_cache[hostname] = coro
    host = await coro
    dns_cache[hostname] = host
    return host


class Transport:
    """
    An asynchronous sockets communication implementation using
    asyncio streams.
    """

    def __init__(self):
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.used: bool = False
        self.message_manager: Buffer = Buffer()
        self.stream_message_manager: StreamBuffer = StreamBuffer()

    async def _send_data(self, raw_data: bytes) -> None:
        """
        An asynchronous alternative for socket.send_all method
        :param raw_data: Data which should be sent
        :type raw_data: bytes

        :returns: None
        """
        self.writer.write(raw_data)
        await self.writer.drain()

    async def _receive_data(self) -> Tuple[None, None] | Tuple[bytes, int]:
        """
        An asynchronous alternative for socket.recv() method.
        """
        data = await self.reader.read(1000)
        resp, without_body_len = self.message_manager.add_data(data)
        return resp, without_body_len

    async def _receive_data_stream(self):
        data = await self.reader.read(20)
        headerless_data = self.stream_message_manager.add_data(data)
        return headerless_data

    async def make_connection(
            self,
            ip: str,
            port: int,
            ssl: bool) -> None:
        """
        An asynchronous alternative for socket connect
        :param ip: Ip where connection should be made
        :type ip: str
        :param port: Connection port
        :type port: int
        :param ssl: True if TLS/SSL should be used
        :type ssl: bool
        :returns: None
        """

        reader, writer = await \
            asyncio.wait_for(asyncio.open_connection(
                host=ip,
                port=port,
                ssl=context if ssl else None
            ),
                timeout=3
            )
        self.reader = reader
        self.writer = writer

    def _check_used(self):
        if self.used:
            raise AsyncRequestsError('Using transport which is already in use')
        self.used = True

    async def send_http_request(self, raw_data: bytes) -> Tuple[bytes, int]:
        """
        The lowest level http request method, can be used directly
        :param raw_data: HTTP message bytes
        :type raw_data: bytes

        :returns: Response bytes and without data len
        :rtype: Tuple[bytes, int]
        """
        self._check_used()
        self.message_manager.set_up()
        await self._send_data(raw_data)
        while True:

            resp, without_body_len = await self._receive_data()
            if resp is not None:
                self.used = False
                return resp, without_body_len

    async def send_http_stream_request(
            self,
            raw_data: bytes):

        self._check_used()
        self.stream_message_manager.set_up()
        await self._send_data(raw_data)

        while True:
            body, done = await self._receive_data_stream()
            if body:
                yield body
            if done:
                break
            await asyncio.sleep(0)

    def is_closing(self) -> bool:
        """
        Wraps transport is_closing
        """
        return self.writer.is_closing()

    def __repr__(self):
        return f"<Transport {'Closed' if self.is_closing() else 'Open'}>"
