import asyncio
import logging
from typing import Awaitable

from ..errors.base import UnexpectedError
from ..errors.requests import RequestTimeoutError
from ..settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)


async def wrap_errors(coro: Awaitable):

    try:
        return await coro
    except asyncio.exceptions.TimeoutError:
        raise RequestTimeoutError(f"Request timeout error")
    except Exception as e:
        log.critical(e)
        raise UnexpectedError(str(e))
