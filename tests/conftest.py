import time
import pytest
import asyncio
import aioreq
import subprocess

SCOPE_SESSION = pytest.fixture(scope='session')
SCOPE_FUNCTION = pytest.fixture(scope='function')
SERVER_URL = 'http://testulik.com'

@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

def temp_function():
    with aioreq.http.Client() as s:
        yield s

@pytest.fixture(scope='session')
def server():
    proc = subprocess.Popen(
            ['uvicorn', 'tests.server.server:app', '--reload', '--port', '7575'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )
    pid = proc.pid
    time.sleep(5)
    print(proc)
    yield SERVER_URL 
    proc.kill()

@pytest.fixture(scope='session')
def get_gzip_url(server):
    return SERVER_URL + '/gzip'

one_time_session = SCOPE_FUNCTION(temp_function)
session = SCOPE_SESSION(temp_function)

