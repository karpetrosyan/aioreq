import asyncio
import logging
import os

import pytest

import aioreq
from aioreq import parse_url
from aioreq.errors.requests import RequestTimeoutError
from aioreq.protocol.http import JsonRequest, Request, StreamClient
from aioreq.protocol.middlewares import MiddleWare
from aioreq.settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)


@pytest.mark.asyncio
async def test_few_requests(
    SERVER_URL,
    temp_session,
):
    t1 = temp_session.get(SERVER_URL)
    t2 = temp_session.get(SERVER_URL)
    t3 = temp_session.get(SERVER_URL)
    tasks = await asyncio.gather(t1, t2, t3)
    assert all([result.status == 200 for result in tasks])


@pytest.mark.asyncio
async def test_normal_request(SERVER_URL, temp_session):
    response = await temp_session.get(SERVER_URL)
    assert response.status == 200


@pytest.mark.asyncio
async def test_moved_301(SERVER_URL, temp_session_redirect_0, redirect_url):
    response = await temp_session_redirect_0.get(redirect_url)
    assert response.status == 301


@pytest.mark.asyncio
async def test_moving_301(SERVER_URL, temp_session, redirect_url):
    response = await temp_session.get(redirect_url)
    assert response.status == 200


@pytest.mark.asyncio
async def test_moving_301_with_directly_request(SERVER_URL, temp_session):
    req = Request(
        url=SERVER_URL,
        method="GET",
        headers={"accept-encoding": "gzip"},
    )
    response = await temp_session.send_request(request=req)
    assert response.status == 200


@pytest.mark.asyncio
async def test_timeout(temp_session, SERVER_URL):
    with pytest.raises(RequestTimeoutError):
        await temp_session.get(SERVER_URL, timeout=0.00001)


@pytest.mark.asyncio
async def test_gzip(temp_session, constants, get_gzip_url):
    expected = constants["GZIP_RESPONSE_TEXT"].encode()
    response = await asyncio.wait_for(temp_session.get(get_gzip_url), timeout=3)
    assert "content-encoding" in response.headers
    # then server sent encoded message!
    assert len(response.content) == len(expected)


@pytest.mark.asyncio
async def test_deflate(temp_session, constants, get_deflate_url):
    expected = constants["DEFLATE_RESPONSE_TEXT"].encode()
    response = await asyncio.wait_for(temp_session.get(get_deflate_url), timeout=3)
    assert "content-encoding" in response.headers
    # then server sent encoded message!
    assert len(response.content) == len(expected)


@pytest.mark.asyncio
async def test_https_request(temp_session, SERVER_URL):
    response = await temp_session.get(SERVER_URL)
    assert response.status == 200


@pytest.mark.asyncio
async def test_dirctly_requests_using(temp_session, SERVER_URL):
    req = Request(
        url=parse_url(SERVER_URL),
        method="GET",
        headers={},
    )

    jsonreq = JsonRequest(
        url=parse_url(SERVER_URL),
        method="GET",
        headers={},
    )

    t1 = asyncio.create_task(temp_session.send_request(req))
    t2 = asyncio.create_task(temp_session.send_request(jsonreq))
    result1, result2 = await asyncio.gather(t1, t2)

    assert result1.status == 200 == result2.status
    assert "content-type" in result1.headers


@pytest.mark.asyncio
async def test_root_with_stream(SERVER_URL, constants, get_stream_test_url):
    t2 = bytearray()
    req = Request(url=get_stream_test_url, method="GET")
    async with StreamClient(request=req) as response:
        assert response.status == 200
        async for chunk in response.content:
            for char in chunk:
                t2.append(char)
    assert t2 == constants["STREAMING_RESPONSE_CHUNK_COUNT"] * b"test"


@pytest.mark.asyncio
async def test_basic_authentication(temp_session, temp_session_without_authorization):
    woauth_resp = temp_session_without_authorization.get(
        "http://httpbin.org/basic-auth/foo/bar", auth=("foo", "bar")
    )
    resp = temp_session.get(
        "http://httpbin.org/basic-auth/foo/bar", auth=("foo", "bar")
    )
    woauth_resp, resp = await asyncio.gather(woauth_resp, resp)
    assert resp.status == 200 and woauth_resp.status == 401


@pytest.mark.asyncio
async def test_add_custom_middleware(temp_session):
    class CustomMiddleWare(MiddleWare):
        async def process(self, request, client):
            return "TEST"

    temp_session.middlewares = CustomMiddleWare(
        next_middleware=temp_session.middlewares
    )
    resp = await temp_session.get("http://test.test")
    assert resp == "TEST"


@pytest.mark.asyncio
async def test_permanent_redirection(SERVER_URL, temp_session, redirect_url):
    resp1 = await temp_session.get(redirect_url)
    resp2 = await temp_session.get(redirect_url)

    assert resp1.redirects == [SERVER_URL + "/redirected"]
    assert not resp2.redirects


@pytest.mark.asyncio
async def test_set_cookie(SERVER_URL, temp_session, set_cookie_url):
    await temp_session.get(set_cookie_url)
    assert "test" in temp_session.cookies.cookies[0].key


@pytest.mark.asyncio
async def test_stream_req_to_youtube():
    req = Request(url="https://www.youtube.com", method="GET")
    async with StreamClient(req) as resp:
        assert resp.status == 200
        async for chunk in resp.content:
            ...


@pytest.mark.asyncio
async def test_req_to_youtube(temp_session):
    await temp_session.get("https://youtube.com")


@pytest.mark.asyncio
async def test_sslkeylog(temp_session_cached, tox):
    temp_session = temp_session_cached
    keylog_file = os.getenv("SSLKEYLOGFILE")
    if not keylog_file:
        assert not tox, "SSLKEYLOGFILE variable must be provided during tox test"
        pytest.skip("SSLKEYLOGFILE variable was not provided")
    await temp_session.get("https://www.github.com")
    assert temp_session.transports
    assert os.path.exists(os.path.join(keylog_file))


@pytest.mark.asyncio
async def test_default_client(temp_session):
    coro1 = temp_session.get("http://127.0.0.1:7575")
    coro2 = temp_session.get("http://127.0.0.1:7575/ping")
    resp3 = aioreq.get("http://127.0.0.1:7575/ping")
    resp1, resp2 = await asyncio.gather(coro1, coro2)
    assert resp1.status == resp2.status == resp3.status == 200
