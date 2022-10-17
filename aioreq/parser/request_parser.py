from ..protocol.http import Request

from abc import ABCMeta
from abc import abstractmethod

class BaseRequestParser(ABCMeta):
    
    @abstractmethod
    def parse(cls, request: Request) -> str:
        ...


class RequestParser(BaseRequestParser):

    @classmethod
    def sum_path_parameters(cls, parameters):
        return "&".join([f"{key}={value}" for key, value in parameters])
            

    @classmethod
    def parse(cls, request: Request) -> str:
        """
        Parsing object type of request to string representing HTTP message

        :returns: raw http request text
        :rtype: str
        """

        if request.path_parameters:
            request.path += '?' + self.sum_path_parameters(request.path_parameters)

        if request.json:
            request.headers['Content-Length'] = len(request.json)
            request.headers['Content-Type'] = "application/json"

        message = ('\r\n'.join((
            f'{request.method} {request.path} {request.scheme_and_version}',
            f'Host:   {request.host}',
            *(f"{key}:  {value}" for key, value in request.headers.items()),
        )) + ('\r\n\r\n'))

        if request.json:
            message += ( 
                  f"{request.json}")

        return message



