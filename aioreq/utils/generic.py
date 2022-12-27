import asyncio
import logging

from ..errors.requests import RequestTimeoutError
from typing import Awaitable
from ..settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)


async def wrap_errors(coro: Awaitable):

    try:
        return await coro
    except asyncio.exceptions.TimeoutError:
        raise RequestTimeoutError(f"Request timeout error")
    except BaseException as e:
        log.critical(f"Unecpected error was raised")
        raise e
