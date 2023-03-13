__version__ = "1.0.6"

import asyncio
from concurrent.futures import ThreadPoolExecutor

from aioreq import http
from aioreq.http import *

try:
    import uvloop  # type: ignore

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    ...

default_client = http.Client()
default_client_executor = ThreadPoolExecutor(1)
default_client_loop = asyncio.new_event_loop()


def wrapper(async_method):
    def inner(*args, **kwargs):
        coro = async_method(*args, **kwargs)
        return default_client_executor.submit(
            default_client_loop.run_until_complete, coro
        ).result()

    return inner


for method in default_client.methods:
    method = method.lower()
    globals()[method] = wrapper(getattr(default_client, method))
