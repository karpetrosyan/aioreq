import logging

from ..settings import LOGGER_NAME
from time import perf_counter
from functools import wraps

log = logging.getLogger(LOGGER_NAME)

def timer(fnc):
    sm = 0
    cnt = 0
    @wraps(fnc)
    def inner(*args, **kwargs):
        nonlocal sm
        nonlocal cnt
        cnt += 1
        t1 = perf_counter()
        result = fnc(*args, **kwargs)
        sm += perf_counter() - t1
        log.debug(f"{fnc.__name__} take summary {sm}")
        log.debug(f"{fnc.__name__} calls count is {cnt}")
        return result
    return inner

