import asyncio
import os
import signal
import subprocess
from time import sleep

import pytest
import pytest_asyncio

import aioreq
from aioreq.protocol.middlewares import default_middlewares

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


def temp_function(persistent_connections=False, stream=False, kwargs=None):
    if kwargs is None:
        kwargs = {}

    async def inner():
        if stream:
            async with aioreq.StreamClient(persistent_connections=persistent_connections, **kwargs) as s:
                yield s
        else:
            async with aioreq.http.Client(persistent_connections=persistent_connections, **kwargs) as s:
                yield s

    return inner


@pytest.fixture(scope='session')
def server():

    proc = subprocess.Popen(
            ['uvicorn', 'tests.server:app', '--port', '7575'],
            stdout=subprocess.PIPE)
    text = proc.stdout.read(7)
    assert text == b'started'
    yield SERVER_URL
    os.kill(proc.pid, signal.SIGKILL)


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


def test_turn_server_on(server):
    ...


one_time_session = SCOPE_FUNCTION(temp_function())
session = SCOPE_SESSION(temp_function())
one_time_session_cached = SCOPE_SESSION(temp_function(persistent_connections=True))
one_time_session_stream = SCOPE_SESSION(temp_function(persistent_connections=False, stream=True))
one_time_session_redirect_0 = SCOPE_SESSION(temp_function(kwargs=dict(redirect_count=0, retry_count=0)))
one_time_session_without_authorization = SCOPE_SESSION(temp_function(kwargs=dict(
    middlewares=[middleware for middleware in default_middlewares if middleware != 'AuthenticationMiddleWare'])))
