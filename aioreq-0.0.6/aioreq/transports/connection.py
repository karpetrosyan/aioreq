import asyncio
import logging
import ssl
from typing import Tuple

import certifi
from dns import asyncresolver

from .buffer import Buffer
from ..errors.requests import AsyncRequestsError
from ..settings import LOGGER_NAME

res = asyncresolver.Resolver()
res.nameservers = ['1.1.1.1']

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
    Ip port resolving by making dns requests
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
        self.reader: None | asyncio.StreamReader = None
        self.writer: None | asyncio.StreamWriter = None
        self.used: bool = False
        self.message_manager: Buffer = Buffer(text='')

    async def send_data(self, raw_data: bytes) -> None:
        """
        An asynchronous alternative for socket.send_all method
        :param raw_data: Data which should be sent
        :type raw_data: bytes

        :returns: None
        """
        self.writer.write(raw_data)
        await self.writer.drain()

    async def receive_data(self) -> Tuple[None, None] | Tuple[bytes, int]:
        """
        An asynchronous alternative for socket.recv() method.
        """
        data = await self.reader.read(10000)
        log.debug(f"Received data : {len(data)} bytes")
        resp, without_body_len = self.message_manager.add_data(data)
        return resp, without_body_len

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

        reader, writer = await asyncio.open_connection(
            host=ip,
            port=port,
            ssl=context if ssl else None
        )
        self.reader = reader
        self.writer = writer

    async def send_http_request(self, raw_data: bytes) -> Tuple[bytes, int]:
        """
        The lowest level http request method, can be used directly
        :param raw_data: HTTP message bytes
        :type raw_data: bytes

        :returns: Response bytes and without data len
        :rtype: Tuple[bytes, int]
        """
        if self.used:
            raise AsyncRequestsError('Using transport which already in use')
        self.used = True
        await self.send_data(raw_data)
        while True:

            resp, without_body_len = await self.receive_data()
            if resp is not None:
                self.used = False
                return resp, without_body_len

    def is_closing(self) -> bool:
        """
        Wraps transport is_closing
        """
        return self.writer.is_closing()
