import re
import asyncio

from dns import resolver
from functools import partial

resolver = resolver.Resolver()
resolver.nameservers = ['8.8.8.8']

url_splitter = re.compile(r'(?P<host>https?//.*?)(?P<path>.*)')
 

def resolve_domain(hostname):
    resolved_data = resolver.resolve(hostname)
    for ip in resolved_data:
        return (ip.address, resolved_data.port)
    
class HttpClientProtocol(asyncio.Protocol):

    def __init__(self):
        ...

    def connection_made(self, transport):
        return 
        data = (
                f"GET /user/me HTTP/1.1\r\n"
                f"Host:192.168.0.185:8000\r\n\r\n"
                )
        # transport.write(b'GET / HTTP/1.1\r\nHost:192.168.0.185:8000\r\n\r\n')
        transport.write(data.encode())

    def data_received(self, data):
        print('Data received: {!r}'.format(data.decode()))

    def connection_lost(self, exc):
        print('The server closed the connection')


class Request:

    @classmethod
    async def create(cls, method, host, headers):
        self         = cls()
        self.host    = host
        self.headers = {}
        self.method  = method


    def __str__(self):
        return (
                f'{self.method} '
                )

class Client:

    def __init__(self):
        self.connection_mapper = {}
        self.headers = {}

    async def get(self, url, *args):
        print(url)
        print(url_splitter.search(url))
        request = await Request.create(
                method = "GET",
                host = url,
                headers = self.headers
                )
        transport = await self.make_connection(url)
         

    async def make_connection(self, host):
        transport = self.connection_mapper.get(host, None)
        if not transport:
            ip, port = resolve_domain(host)
            ip = '192.168.0.185'
            port = 8000
            loop = asyncio.get_event_loop()
            connection_coroutine = loop.create_connection(
                    lambda: HttpClientProtocol(),
                    host=ip,
                    port=port
                        )
            transport, protocol = await asyncio.wait_for(connection_coroutine, timeout=3)
            self.connection_mapper[host] = transport
        return transport
    

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        for host, transport in self.connection_mapper.items():
            value.close()
