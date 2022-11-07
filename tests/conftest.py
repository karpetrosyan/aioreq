import time
import pytest
import asyncio
import aioreq
import subprocess
import pytest_asyncio

from functools import wraps 

SCOPE_SESSION = pytest_asyncio.fixture(scope='session')
SCOPE_FUNCTION = pytest_asyncio.fixture(scope='function')
SERVER_URL = 'http://testulik.com'


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

def temp_function(persistent_connections=False):
    
    async def inner():
        async with aioreq.http.Client(persistent_connections=persistent_connections) as s:
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
one_time_session_cached = SCOPE_SESSION(temp_function(persistent_connections=True))

