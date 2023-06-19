import asyncio
import logging
import os
import ssl as _ssl
from abc import ABC
from abc import abstractmethod
from contextlib import contextmanager
from enum import Enum
from typing import AsyncGenerator
from typing import Awaitable
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Union

from dns import asyncresolver  # type: ignore

from aioreq.settings import LOGGER_NAME

STREAM_BUFFER_SIZE = 1024 * 4  # 4Kb
res = asyncresolver.Resolver()
res.nameservers = ["1.1.1.1", "8.8.8.8"]

log = logging.getLogger(LOGGER_NAME)


def load_ssl_context(
    check_hostname: bool = True,
    verify_mode: bool = True,
    keylog_filename: Optional[str] = None,
) -> _ssl.SSLContext:
    context = _ssl.create_default_context()
    context.keylog_filename = keylog_filename or os.getenv(  # type: ignore
        "SSLKEYLOGFILE"
    )
    context.check_hostname = check_hostname
    context.verify_mode = verify_mode  # type: ignore
    return context


async def get_address(host):
    answers = await res.resolve(host)
    return answers.rrset[0].address  # type: ignore


dns_cache: Dict[str, Union[str, Awaitable]] = dict()


@contextmanager
def mock_transport(transport):
    transport.used = True
    yield
    transport.used = False


@contextmanager
def change_stream_state(stream: "StreamReader"):
    if stream.state != StreamState.CREATED:
        raise Exception(f"Can not read the stream with the `{stream.state}` state")
    stream.state = StreamState.READING
    yield
    stream.state = StreamState.CLOSED


async def resolve_domain(
    url,
) -> Tuple[str, int]:
    hostname = url.ip or ".".join(url.host)

    port = url.port
    ip = url.ip

    if port is None:
        port = 80 if url.scheme == "http" else 443

    if ip is not None:
        return ip, port

    if hostname in dns_cache:
        memo = dns_cache[hostname]
        if isinstance(memo, str):
            return memo, port
        else:
            return await memo, port

    log.trace(f"trying resolve hostname={hostname}")  # type: ignore
    coro = asyncio.create_task(get_address(hostname))
    dns_cache[hostname] = coro
    ip = await coro
    dns_cache[hostname] = ip
    return ip, port


class StreamState(Enum):
    CREATED = "CREATED"
    READING = "READING"
    CLOSED = "CLOSED"


class StreamReader(ABC):
    def __init__(self, reader: asyncio.StreamReader):
        self.state: StreamState = StreamState.CREATED
        self.reader = reader

    @abstractmethod
    async def read_by_chunks(self, max_read: int) -> AsyncGenerator[bytes, None]:
        yield b""


class ByteStreamReader(StreamReader):
    def __init__(self, reader: asyncio.StreamReader, to_read: int):
        super().__init__(reader=reader)
        self.to_read = to_read

    async def read_by_chunks(self, max_read: int) -> AsyncGenerator[bytes, None]:
        with change_stream_state(self):
            while True:
                if max_read >= self.to_read:
                    yield await self.reader.readexactly(self.to_read)
                    break
                yield await self.reader.read(max_read)
                self.to_read -= max_read


class ChunkedStreamReader(StreamReader):
    async def read_by_chunks(self, max_read: int) -> AsyncGenerator[bytes, None]:
        with change_stream_state(self):
            while True:
                chunk = await self.reader.readuntil(b"\r\n")
                chunk_size = chunk[:-2]
                if b";" in chunk_size:
                    chunk_size = chunk_size.split(b";")[0].strip()
                chunk_size = int(chunk_size, 16)
                if chunk_size == 0:
                    break

                while chunk_size:
                    if max_read >= chunk_size:
                        yield await self.reader.readexactly(chunk_size)
                        break
                    else:
                        yield await self.reader.readexactly(max_read)
                        chunk_size -= max_read
                await self.reader.readexactly(2)  # skip crlf


class Transport:
    def __init__(self):
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.used: bool = False

    async def _send_data(self, raw_data: bytes) -> None:
        assert self.writer
        self.writer.write(raw_data)
        await self.writer.drain()

    async def make_connection(
        self,
        ip: str,
        port: int,
        ssl: bool,
        server_hostname: Optional[str],
        verify_mode: bool,
        check_hostname: bool,
        keylog_filename: Optional[str],
    ) -> None:
        log.trace(f"{ip}, {port}")  # type: ignore

        if ssl:
            context = load_ssl_context(
                verify_mode=verify_mode,
                check_hostname=check_hostname,
                keylog_filename=keylog_filename,
            )
            reader, writer = await asyncio.open_connection(
                host=ip,
                port=port,
                ssl=context,
                server_hostname=server_hostname,
            )
        else:
            reader, writer = await asyncio.open_connection(
                host=ip,
                port=port,
                ssl=None,
                server_hostname=None,
            )
        self.reader = reader
        self.writer = writer

    async def send_http_request(
        self, raw_data: bytes, stream: bool
    ) -> Tuple[str, str, Union[bytes, StreamReader]]:
        with mock_transport(self):
            await self._send_data(raw_data)
            from aioreq import ResponseParser

            assert self.reader
            status_line = (await self.reader.readuntil(b"\r\n")).decode()
            headers_line = (await self.reader.readuntil(b"\r\n\r\n")).decode()
            content_length = ResponseParser.search_content_length(headers_line)
            
            if content_length is not None:
                return (
                    status_line,
                    headers_line,
                    ByteStreamReader(reader=self.reader, to_read=content_length)
                    if stream
                    else await self.reader.readexactly(content_length),
                )
            elif ResponseParser.search_transfer_encoding(headers_line):
                if stream:
                    return status_line, headers_line, ChunkedStreamReader(self.reader)
                else:
                    content = b""
                    async for chunk in ChunkedStreamReader(self.reader).read_by_chunks(
                        max_read=2048
                    ):
                        content += chunk
                    return status_line, headers_line, content
            else:
                raise Exception(
                    "`Content-Length` or `Transfer-Encoding: "
                    "Chunked` must be specified in the response headers"
                )

    def is_closing(self) -> bool:
        """
        Wraps transport is_closing
        """
        if self.writer:
            return self.writer.is_closing()
        raise TypeError("`is_closing` method called on unconnected transport")

    def __repr__(self):
        return f"<Transport {'Closed' if self.is_closing() else 'Open'}>"
