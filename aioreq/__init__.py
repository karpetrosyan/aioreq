import asyncio

from .protocol import http
from .protocol import headers
from .errors import requests
from .errors import response
from .errors import base
from .parser import request_parser
from .parser import response_parser
from .parser import url_parser
from .transports import connection

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except:
    ...
