import asyncio
import contextlib
import logging

from aioreq.errors.requests import RequestTimeoutError
from aioreq.settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)


@contextlib.contextmanager
def wrap_errors():
    try:
        yield
    except asyncio.TimeoutError:
        raise RequestTimeoutError
