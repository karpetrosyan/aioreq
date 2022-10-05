
class Response:

    def __init__(
            self,
            scheme : str,
            status : int,
            status_message : str,
            headers : dict,
            body : str):
        self.scheme_and_version = scheme
        self.status = status
        self.status_message = status_message
        self.headers = headers
        self.body = body

class Request:

    @classmethod
    async def create(cls, method, host, headers, path) -> 'Request':
        self         = cls()
        self.host    = host
        self.headers = {}
        self.method  = method
        self.path    = path
        return self

    def __str__(self) -> 'Request':
        return '\r\n'.join((
                f'{self.method} {self.path} HTTP/1.1',
                f'Host:   {self.host}',
                *(f"{key}:  {value}" for key, value in self.headers.items())
                )) + '\r\n\r\n'


