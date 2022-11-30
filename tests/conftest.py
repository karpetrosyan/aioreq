import pytest
import asyncio
import aioreq
import subprocess
import pytest_asyncio

SCOPE_SESSION = pytest_asyncio.fixture(scope='session')
SCOPE_FUNCTION = pytest_asyncio.fixture(scope='function')
SERVER_URL = 'http://testulik.com'

# Server constants
CONSTANTS = dict(
    GZIP_RESPONSE_TEXT="testgzip" * 10000,
    STREAMING_RESPONSE_CHUNK_COUNT=30,
    DEFLATE_RESPONSE_TEXT='testdeflate' * 10000,
)


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def temp_function(persistent_connections=False, stream=False):
    async def inner():
        if stream:
            async with aioreq.StreamClient(persistent_connections=persistent_connections) as s:
                yield s
        else:
            async with aioreq.http.Client(persistent_connections=persistent_connections) as s:
                yield s

    return inner


@pytest.fixture(scope='session')
def server():
    proc = subprocess.Popen(
        ['uvicorn', 'tests.server:app', '--port', '7575'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    pid = proc.pid
    text = proc.stdout.read(7).decode()
    assert text == 'started'

    yield SERVER_URL
    subprocess.run(['kill', str(pid)])


@pytest.fixture(scope='session')
def get_gzip_url(server):
    return SERVER_URL + '/gzip'


@pytest.fixture(scope='session')
def get_deflate_url(server):
    return SERVER_URL + '/deflate'


@pytest.fixture(scope='session')
def get_stream_test_url(server):
    return SERVER_URL + '/test_stream'


@pytest.fixture(scope='session')
def constants():
    return CONSTANTS


one_time_session = SCOPE_FUNCTION(temp_function())
session = SCOPE_SESSION(temp_function())
one_time_session_cached = SCOPE_SESSION(temp_function(persistent_connections=True))
one_time_session_stream = SCOPE_SESSION(temp_function(persistent_connections=False, stream=True))
