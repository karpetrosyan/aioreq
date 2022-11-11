import asyncio
import logging

from ..errors.requests import RequestTimeoutError
from typing import Awaitable
from ..settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)


async def wrap_errors(coro: Awaitable, timeout: int):
    try:
        if timeout:
            return await asyncio.wait_for(coro, timeout=timeout)
        return await coro
    except asyncio.exceptions.TimeoutError as e:
        raise RequestTimeoutError(f"Request timeout error")
    except BaseException as e:
        log.critical(f"Unecpected error was raised")
        raise e
