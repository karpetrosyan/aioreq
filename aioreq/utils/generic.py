import asyncio
import logging
from typing import Awaitable

from ..errors.base import UnexpectedError
from ..errors.requests import RequestTimeoutError
from ..settings import LOGGER_NAME
import contextlib

log = logging.getLogger(LOGGER_NAME)


@contextlib.contextmanager
def wrap_errors():

    try:
        yield
    except asyncio.TimeoutError:
        raise RequestTimeoutError
