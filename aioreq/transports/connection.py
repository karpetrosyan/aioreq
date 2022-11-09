import ssl
import socket
import certifi
import asyncio
import random
import logging

from ..settings import LOGGER_NAME
from .buffer import Buffer
from concurrent.futures import ThreadPoolExecutor

from typing import Tuple

from dns import resolver

res = resolver.Resolver()
res.nameservers = ['1.1.1.1']

log = logging.getLogger(LOGGER_NAME)

context = ssl.SSLContext(ssl.PROTOCOL_TLS)
context.load_verify_locations(certifi.where())

executor = ThreadPoolExecutor(2)

def get_address(host):
    answers = res.query(host)

    for rdata in answers:
        return rdata.address

async def resolve_domain(
                         hostname: str,
                         memo = {}
                         )-> tuple[str, int]:
    """
    Ip port resolving by making dns requests

    :param hostname: Domain name for example youtube.com
    :returns: ip and port for that domain
    :rtype: [str, int]
    """
    if hostname in memo:
        if not isinstance(memo[hostname], str):
            log.debug('Got cached dns query')
            return await memo[hostname]
        return memo[hostname]

    log.debug(f"trying resolve {hostname=}")
    loop = asyncio.get_event_loop()
    coro = loop.run_in_executor(executor, lambda: socket.gethostbyname(hostname))
    memo[hostname] = coro
    host = await coro
    memo[hostname] = host
    return host

class Transport:

    def __init__(self):
        self.reader: None | asyncio.StreamReader = None
        self.writer: None | asyncio.StreamWriter = None
        self.used: bool = False
        self.message_manager: Buffer = Buffer(text='')
   
    async def send_data(self, raw_data: bytes) -> None:
        self.writer.write(raw_data)
        await self.writer.drain()

    async def receive_data(self) -> Tuple[None, None] | Tuple[bytes, int]:
        data = await self.reader.read(100000)
        log.debug(f"Received data : {len(data)} bytes")
        resp, without_body_len = self.message_manager.add_data(data)
        return resp, without_body_len

    async def make_connection(
            self, 
            ip: str, 
            port: int,
            ssl: bool) -> None:
        reader, writer = await asyncio.open_connection(
                                                        host = ip,
                                                        port = port,
                                                        ssl = context if ssl else None
                                                        )
        self.reader = reader
        self.writer = writer

    async def send_http_request(self, raw_data: bytes) -> bytes:
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
        return self.transport.is_closing()
