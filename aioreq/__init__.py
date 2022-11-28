__version__ = '0.0.7'

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
