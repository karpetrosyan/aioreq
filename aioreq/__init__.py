__version__ = "1.0.2b0"

from .protocol import headers
from .protocol import http
from .protocol import middlewares
from .protocol.http import *

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except:
    ...
