__version__ = '0.0.6'

import asyncio

from .protocol import http
from .protocol.http import *

try:
    import uvloop

    # asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except:
    ...
