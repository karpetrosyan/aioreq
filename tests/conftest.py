import time
import pytest
import asyncio
import aioreq
import subprocess

from functools import wraps 

SCOPE_SESSION = pytest.fixture(scope='session')
SCOPE_FUNCTION = pytest.fixture(scope='function')
SERVER_URL = 'http://testulik.com'

loop = asyncio.get_event_loop()

@pytest.fixture(scope='session')
def sdfevent_loop():
    yield loop
    loop.close()

def temp_function(cache_connections=False):

    def inner():
        with aioreq.http.Client(cache_connections=cache_connections) as s:
         yield s
    return inner

@pytest.fixture(scope='session')
def server():
    proc = subprocess.Popen(
            ['uvicorn', 'tests.server.server:app', '--reload', '--port', '7575'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )
    pid = proc.pid
    time.sleep(5)
    yield SERVER_URL 
    subprocess.run(['kill', str(pid)])

@pytest.fixture(scope='session')
def get_gzip_url(server):
    return SERVER_URL + '/gzip'

one_time_session = SCOPE_FUNCTION(temp_function())
session = SCOPE_SESSION(temp_function())
one_time_session_cached = SCOPE_SESSION(temp_function(cache_connections=True))

