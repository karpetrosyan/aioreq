import asyncio

class HttpClientProtocol(asyncio.Protocol):

    def __init__(self, message, on_con_lost):
        self.message = message
        self.on_con_lost = on_con_lost

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
        self.on_con_lost.set_result(True)


class Request:

    @classmethod
    async def create(cls, host, headers):
        self         = cls()
        self.host    = host
        self.headers = {}
        self.status  = None



class Client(asyncio.Protocol):
    

    def __init__(self, host):
        self.connected = False
        self.headers = {}
        self.host = host

    async def get(self, *args):
        request = Request.create()
      
    async def made_connection(self):
        self.connected = True

    async def __aenter__(self):
        if not self.connected:
            await self.made_connection
        return self

    async def __aexit__(self, *args, **kwargs):
        ...

    def parse(self):
        parsed_request =
        


async def main():
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    loop = asyncio.get_running_loop()

    on_con_lost = loop.create_future()
    message = 'Hello World!'
    

    data = (
            f"GET /user/me HTTP/1.1\r\n"
            f"Host:192.168.0.185:8000\r\n\r\n"
            )

    transport, protocol = await loop.create_connection(
        lambda: EchoClientProtocol(message, on_con_lost),
        '192.168.0.185', 8000)

    transport.write(data.encode())
    # Wait until the protocol signals that the connection
    # is lost and close the transport.
    try:
        await on_con_lost
    finally:
        transport.close()


asyncio.run(main())
