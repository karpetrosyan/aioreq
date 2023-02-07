__version__ = "1.0.2"

import asyncio

from .protocol import headers, http, middlewares
from .protocol.http import *

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except:
    ...
