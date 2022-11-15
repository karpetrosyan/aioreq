import logging

from ..settings import LOGGER_NAME
from time import perf_counter
from functools import wraps

log = logging.getLogger(LOGGER_NAME)
function_logs = {}

def timer(fnc):
    if fnc not in function_logs:
        function_logs[fnc] = {
            'name' : fnc.__name__,
            'time' : 0,
            'call_count': 0
        }
    
    @wraps(fnc)
    def inner(*args, **kwargs):
        function_logs[fnc]['call_count'] += 1
        t1 = perf_counter()
        result = fnc(*args, **kwargs)
        function_logs[fnc]['time'] += perf_counter() - t1
        return result
    return inner

