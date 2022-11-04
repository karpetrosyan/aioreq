import ssl
import socket
import certifi
import asyncio
import random
import logging

from ..settings import LOGGER_NAME
from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger(LOGGER_NAME)

context = ssl.SSLContext(ssl.PROTOCOL_TLS)
context.load_verify_locations(certifi.where())

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
        return memo[hostname]

    log.debug(f"trying resolve {hostname=}")
    loop = asyncio.get_event_loop()
    host = await loop.run_in_executor(executor, lambda: socket.gethostbyname(hostname))
    memo[hostname] = host
    return host

class Transport:

    def __init__(self):
        from ..protocol.http import PendingMessage
        self.reader: None | asyncio.StreamReader = None
        self.writer: None | asyncio.StreamWriter = None
        self.used: bool = False
        self.message_manager: PendingMessage = PendingMessage(text='')
   
    async def send_data(self, raw_data: bytes) -> None:
        self.writer.write(raw_data)
        await self.writer.drain()

    async def receive_data(self) -> None | bytes:
        data = await self.reader.read(100000)
        log.debug(f"Received data : {len(data)} bytes")
        resp = self.message_manager.add_data(data)
        return resp

    async def make_connection(
            self, 
            ip: str, 
            port: int,
            ssl: bool) -> None:
        reader, writer = await asyncio.open_connection(
                                                        host = ip,
                                                        port = port,
                                                        ssl = context if ssl else None)
        self.reader = reader
        self.writer = writer

    async def send_http_request(self, raw_data: bytes) -> bytes:
        log.debug(f"sent")
        await self.send_data(raw_data)
        while True:
#            await asyncio.sleep(random.randint(0, 3))
            resp = await self.receive_data()
            if resp is not None:
                return resp
    
    def is_closing(self) -> bool:
        return self.transport.is_closing()
