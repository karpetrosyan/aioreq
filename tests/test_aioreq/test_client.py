import asyncio

import pytest
import logging

from aioreq.settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)

from aioreq.protocol.http import JsonRequest
from aioreq.protocol.http import Request
from aioreq.protocol.http import StreamClient
from aioreq.protocol.middlewares import MiddleWare
from aioreq.errors.requests import RequestTimeoutError


@pytest.mark.asyncio
async def test_few_requests(server, one_time_session, event_loop):
    t1 = one_time_session.get("http://testulik.com")
    t2 = one_time_session.get("http://testulik.com")
    t3 = one_time_session.get("http://testulik.com")
    tasks = await asyncio.gather(t1, t2, t3)
    assert all([result.status == 200 for result in tasks])


@pytest.mark.asyncio
async def test_normal_request(server, one_time_session):
    url = "http://testulik.com"
    response = await one_time_session.get(url)
    assert response.status == 200


@pytest.mark.asyncio
async def test_moved_301(server, one_time_session_redirect_0):
    url = "http://testulik.com/redirect"
    response = await one_time_session_redirect_0.get(url)
    assert response.status == 301


@pytest.mark.asyncio
async def test_moving_301(server, one_time_session):
    url = "http://testulik.com/redirect"
    response = await one_time_session.get(url)
    assert response.status == 200


@pytest.mark.asyncio
async def test_moving_301_with_directly_request(one_time_session):
    url = "http://testulik.com"
    req = Request(
        url=url,
        method="GET",
        headers={"accept-encoding": "gzip"},
    )
    response = await one_time_session.send_request(request=req)
    assert response.status == 200


@pytest.mark.asyncio
async def test_timeout(one_time_session, server):
    with pytest.raises(RequestTimeoutError):
        await one_time_session.get(server, timeout=0.00001)


@pytest.mark.asyncio
async def test_gzip(one_time_session, constants, get_gzip_url):
    expected = constants["GZIP_RESPONSE_TEXT"].encode()
    response = await asyncio.wait_for(one_time_session.get(get_gzip_url), timeout=3)
    assert "content-encoding" in response.headers
    # then server sent encoded message!
    assert len(response.content) == len(expected)


@pytest.mark.asyncio
async def test_deflate(one_time_session, constants, get_deflate_url):
    expected = constants["DEFLATE_RESPONSE_TEXT"].encode()
    response = await asyncio.wait_for(one_time_session.get(get_deflate_url), timeout=3)
    assert "content-encoding" in response.headers
    # then server sent encoded message!
    assert len(response.content) == len(expected)


@pytest.mark.asyncio
async def test_https_request(one_time_session):
    url = "http://www.testulik.com"
    response = await one_time_session.get(url)
    assert response.status == 200


@pytest.mark.asyncio
async def test_dirctly_requests_using(one_time_session, event_loop):
    req = Request(
        url="http://testulik.com/",
        method="GET",
        headers={},
    )

    jsonreq = JsonRequest(
        url="http://testulik.com/",
        method="GET",
        headers={},
    )

    t1 = asyncio.create_task(one_time_session.send_request(req))
    t2 = asyncio.create_task(one_time_session.send_request(jsonreq))
    result1, result2 = await asyncio.gather(t1, t2)

    assert result1.status == 200 == result2.status
    assert "content-type" in result1.headers


@pytest.mark.asyncio
async def test_root_with_stream(server, constants, get_stream_test_url):
    t2 = bytearray()
    req = Request(url=get_stream_test_url, method="GET")
    async with StreamClient(request=req) as response:
        assert response.status == 200
        async for chunk in response.content:
            log.critical(chunk)
            for char in chunk:
                t2.append(char)
    assert t2 == constants["STREAMING_RESPONSE_CHUNK_COUNT"] * b"test"


@pytest.mark.asyncio
async def test_basic_authentication(
    one_time_session, one_time_session_without_authorization
):
    woauth_resp = one_time_session_without_authorization.get(
        "http://httpbin.org/basic-auth/foo/bar", auth=("foo", "bar")
    )
    resp = one_time_session.get(
        "http://httpbin.org/basic-auth/foo/bar", auth=("foo", "bar")
    )
    woauth_resp, resp = await asyncio.gather(woauth_resp, resp)
    assert resp.status == 200 and woauth_resp.status == 401


@pytest.mark.asyncio
async def test_add_custom_middleware(one_time_session):
    class CustomMiddleWare(MiddleWare):
        async def process(self, request, client):
            return "TEST"

    one_time_session.middlewares = CustomMiddleWare(
        next_middleware=one_time_session.middlewares
    )
    resp = await one_time_session.get("http://test.test")
    assert resp == "TEST"
