import asyncio
import logging
import os
import ssl
from typing import Coroutine, Awaitable, Optional
from typing import Dict
from typing import Tuple
from typing import Union
from ..settings import TEST_SERVER_DOMAIN
import certifi
from dns import asyncresolver

from ..errors.requests import AsyncRequestsError
from ..settings import LOGGER_NAME

res = asyncresolver.Resolver()
res.nameservers = ["1.1.1.1", "8.8.8.8"]

log = logging.getLogger(LOGGER_NAME)

context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.maximum_version = ssl.TLSVersion.TLSv1_2

context.load_verify_locations(certifi.where())
context.keylog_filename = os.getenv("SSLKEYLOGFILE")  # type: ignore

context.check_hostname = False


async def get_address(host):
    answers = await res.resolve(host)
    return answers.rrset[0].address


dns_cache: Dict[str, Union[str, Awaitable]] = dict()


async def resolve_domain(
        url,
):
    """
    Makes an asynchronous DNS request to resolve the IP address
    :param hostname: Domain name for example YouTube.com
    :type hostname: str
    :returns: ip and port for that domain
    :rtype: [str, int]
    """

    hostname = url.get_url_for_dns()
    if url.domain == TEST_SERVER_DOMAIN:
        return 'localhost', 7575

    port = 80 if url.protocol == 'http' else 443
    if hostname in dns_cache:
        memo = dns_cache[hostname]
        if isinstance(memo, str):
            return memo, port
        else:
            return await memo, port

    log.trace(f"trying resolve hostname={hostname}")  # type: ignore
    coro = asyncio.create_task(get_address(hostname))
    dns_cache[hostname] = coro
    host = await coro
    dns_cache[hostname] = host
    return host, port


class Transport:
    """
    An asynchronous sockets communication implementation using
    asyncio streams.
    """

    def __init__(self):
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.used: bool = False

    async def _send_data(self, raw_data: bytes) -> None:
        """
        An asynchronous alternative for socket.send_all method
        :param raw_data: Data which should be sent
        :type raw_data: bytes

        :returns: None
        """
        assert self.writer
        self.writer.write(raw_data)
        await self.writer.drain()

    async def make_connection(self, ip: str, port: int, ssl: bool) -> None:
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
        log.trace(f"{ip}, {port}")
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host=ip, port=port, ssl=context if ssl else None),
            timeout=3,
        )
        self.reader = reader
        self.writer = writer

    def _check_used(self):
        if self.used:
            raise AsyncRequestsError("Using transport which is already in use")
        self.used = True

    async def send_http_request(self, raw_data: bytes):
        """
        The lowest level http request method, can be used directly
        :param raw_data: HTTP message bytes
        :type raw_data: bytes

        :returns: Response bytes and without data len
        :rtype: Tuple[bytes, int]
        """

        self._check_used()
        await self._send_data(raw_data)
        from aioreq import ResponseParser
        assert self.reader
        status_line = await self.reader.readuntil(b'\r\n')
        status_line = status_line.decode()
        headers_line = await self.reader.readuntil(b'\r\n\r\n')
        headers_line = headers_line.decode()
        content_length = ResponseParser.search_content_length(headers_line)
        content = b""

        if content_length is not None:
            content = await self.reader.readexactly(content_length)
        else:
            while True:
                chunk = await self.reader.readuntil(b'\r\n')
                chunk_size = chunk[:-2]

                chunk_size = int(chunk_size, 16)
                if chunk_size == 0:
                    break
                data = await self.reader.readexactly(chunk_size)
                crlf = await self.reader.readexactly(2)
                content += data

        return status_line, headers_line, content

    async def send_http_stream_request(self, raw_data: bytes):
        """
        The lowest level http request method, can be used directly
        :param raw_data: HTTP message bytes
        :type raw_data: bytes

        :returns: Response bytes and without data len
        :rtype: Tuple[bytes, int]
        """
        from aioreq import ResponseParser

        self._check_used()
        await self._send_data(raw_data)
        assert self.reader
        status_line = await self.reader.readuntil(b'\r\n')
        status_line = status_line.decode()
        headers_line = await self.reader.readuntil(b'\r\n\r\n')
        headers_line = headers_line.decode()
        content_length = ResponseParser.search_content_length(headers_line)

        yield status_line, headers_line
        if content_length is not None:
            raise TypeError("Stream request should use chunked")
        else:
            while True:
                chunk = await self.reader.readuntil(b'\r\n')
                chunk_size = chunk[:-2]

                chunk_size = int(chunk_size, 16)
                if chunk_size == 0:
                    break
                data = await self.reader.readexactly(chunk_size)
                crlf = await self.reader.readexactly(2)
                yield data

    def is_closing(self) -> bool:
        """
        Wraps transport is_closing
        """
        if self.writer:
            return self.writer.is_closing()
        raise TypeError("`is_closing` method called on unconnected transport")

    def __repr__(self):
        return f"<Transport {'Closed' if self.is_closing() else 'Open'}>"
