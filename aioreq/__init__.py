__version__ = '1.0.0b1'

import asyncio

from .protocol import http
from .protocol.http import *
from .protocol import headers

try:
    ...
    # import uvloop

    # asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except:
    ...
