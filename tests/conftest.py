import logging
import os
import subprocess
import warnings

import pytest
import pytest_asyncio

import aioreq
from aioreq.middlewares import default_middlewares
from aioreq.settings import LOGGER_NAME

warnings.filterwarnings("ignore")

log = logging.getLogger(LOGGER_NAME)

CONSTANTS = dict(
    GZIP_RESPONSE_TEXT="testgzip" * 10000,
    STREAMING_RESPONSE_CHUNK_COUNT=30,
    DEFLATE_RESPONSE_TEXT="testdeflate" * 10000,
    SERVER_URL="http://127.0.0.1:7575",
)


def pytest_addoption(parser):
    parser.addoption("--tox", action="store_true", default=False)


def pytest_sessionfinish(session, exitstatus):
    fl = os.getenv("SSLKEYLOGFILE")
    if session.config.option.tox:
        if fl:
            tests_logs = os.path.join("tests", fl)
            if os.path.exists(fl):
                os.remove(fl)
                log.debug(f"Logs file found and removed from the {fl}")
            if os.path.exists(tests_logs):
                os.remove(tests_logs)
                log.debug(f"Logs file found and removed from the {tests_logs}")


@pytest.fixture(autouse=True, scope="session")
def session_start():
    log.debug("Running server process")
    with subprocess.Popen(
        ["uvicorn", "tests.server:app", "--log-level", "critical", "--port", "7575"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        log.debug("Waiting signal from the server process")
        assert proc.stdout.readline() == b"started\n"
        log.debug("Signal was received from the server process")
        yield
        log.debug("Teardown server process")
        proc.terminate()
        log.debug("Server process was terminated")


@pytest.fixture(scope="session")
def tox(pytestconfig):
    return pytestconfig.getoption("tox")


@pytest.fixture(scope="session")
def SERVER_URL(session_start):
    return CONSTANTS["SERVER_URL"]


@pytest.fixture(scope="session")
def get_gzip_url(SERVER_URL):
    return SERVER_URL + "/gzip"


@pytest.fixture(scope="session")
def get_deflate_url(SERVER_URL):
    return SERVER_URL + "/deflate"


@pytest.fixture(scope="session")
def get_stream_test_url(SERVER_URL):
    return SERVER_URL + "/test_stream"


@pytest.fixture(scope="session")
def redirect_url(SERVER_URL):
    return SERVER_URL + "/redirect"


@pytest_asyncio.fixture()
async def set_cookie_url(SERVER_URL):
    return SERVER_URL + "/set-cookie"


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
