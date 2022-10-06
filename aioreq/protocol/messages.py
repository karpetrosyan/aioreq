
class Response:

    def __init__(
            self,
            scheme_and_version : str,
            status : int,
            status_message : str,
            headers : dict,
            body : str):
        self.scheme_and_version = scheme_and_version
        self.status = status
        self.status_message = status_message
        self.headers = headers
        self.body = body

    def __repr__(self):
        return '\n'.join((
                f"Response(",
                f"\tscheme_and_version='{self.scheme_and_version}'",
                f"\tstatus = {self.status}",
                f"\tstatus_message = '{self.status_message}'",
                *(
                    f"\t{key}: {value}" for key, value in self.headers.items()
                    ),
                ')'
                ))

class Request:

    @classmethod
    async def create(cls, method, host, headers, path) -> 'Request':
        self         = cls()
        self.host    = host
        self.headers = {}
        self.method  = method
        self.path    = path
        return self

    def get_raw_request(self) -> str:
        return ('\r\n'.join((
                f'{self.method} {self.path} HTTP/1.1',
                f'Host:   {self.host}',
                *(f"{key}:  {value}" for key, value in self.headers.items())
                )) + '\r\n\r\n').encode('utf-8')


