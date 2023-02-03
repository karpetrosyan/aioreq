import asyncio
import os
import signal
import subprocess

import pytest
import pytest_asyncio

import aioreq
from aioreq.protocol.middlewares import default_middlewares

SERVER_URL = "http://127.0.0.1:7575"

# Server constants
CONSTANTS = dict(
    GZIP_RESPONSE_TEXT="testgzip" * 10000,
    STREAMING_RESPONSE_CHUNK_COUNT=30,
    DEFLATE_RESPONSE_TEXT="testdeflate" * 10000,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def temp_function(persistent_connections=False, kwargs=None):
    if kwargs is None:
        kwargs = {}

    async def inner():
        async with aioreq.http.Client(
            persistent_connections=persistent_connections, **kwargs
        ) as s:
            yield s

    return inner


@pytest.fixture(scope="session")
def server():
    ...
    proc = subprocess.Popen(
        ["uvicorn", "tests.server:app", "--port", "7575"], stdout=subprocess.PIPE
    )
    text = proc.stdout.read(7)
    assert text == b"started"
    yield SERVER_URL
    os.kill(proc.pid, signal.SIGTERM)


@pytest.fixture(scope="session")
def get_gzip_url(server):
    return SERVER_URL + "/gzip"


@pytest.fixture(scope="session")
def get_deflate_url(server):
    return SERVER_URL + "/deflate"


@pytest.fixture(scope="session")
def get_stream_test_url(server):
    return SERVER_URL + "/test_stream"


@pytest.fixture(scope="session")
def redirect_url(server):
    return SERVER_URL + "/redirect"


@pytest.fixture(scope="session")
def constants():
    return CONSTANTS


@pytest_asyncio.fixture()
async def temp_session():
    async with aioreq.http.Client() as s:
        yield s


@pytest_asyncio.fixture()
async def temp_session_cached():
    async with aioreq.http.Client(persistent_connections=True) as s:
        yield s


@pytest_asyncio.fixture()
async def temp_session_redirect_0():
    async with aioreq.http.Client(redirect_count=0, retry_count=0) as s:
        yield s


@pytest_asyncio.fixture()
async def temp_session_without_authorization():
    middlewares = [
        middleware
        for middleware in default_middlewares
        if middleware != "AuthenticationMiddleWare"
    ]
    async with aioreq.http.Client(middlewares=middlewares) as s:
        yield s

@pytest_asyncio.fixture()
async def set_cookie_url():
    return SERVER_URL + '/set-cookie'

def test_turn_server_on(server):
    ...
