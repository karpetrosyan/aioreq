import pytest
import asyncio

from aioreq.errors.requests import AsyncRequestsError
from aioreq.protocol.http import Request
from aioreq.protocol.http import JsonRequest


@pytest.mark.asyncio
async def test_few_requests(one_time_session, event_loop):
    t1 = one_time_session.get('https://www.facebook.com')
    t2 = one_time_session.get('https://www.google.com')
    t3 = one_time_session.get('https://www.youtube.com')
    tasks = await asyncio.gather(t1, t2, t3)
    assert all([result.status == 200 for result in tasks])


@pytest.mark.asyncio
async def test_normal_request(one_time_session):
    url = 'http://youtube.com'
    response = await one_time_session.get(url)
    assert response.status == 200


@pytest.mark.asyncio
async def test_moved_301(one_time_session):
    url = 'http://google.com'
    response = await one_time_session.get(url, retry=0, redirect=0)
    assert response.status in (301, 302)


@pytest.mark.asyncio
async def test_moving_301(one_time_session):
    url = 'http://google.com'
    response = await one_time_session.get(url, retry=0, redirect=1)
    assert response.status == 200


@pytest.mark.asyncio
async def test_moving_301_with_directly_request(one_time_session):
    url = 'http://google.com'
    req = Request(
        url=url,
        method='GET',
        headers={'accept-encoding': 'gzip'},
    )
    response = await one_time_session.send_request(request=req)
    assert response.status == 200


@pytest.mark.asyncio
async def test_ping(one_time_session,
                    server):
    response = await one_time_session.get(server, timeout=3)
    assert response.status == 200


@pytest.mark.asyncio
async def test_gzip(one_time_session,
                    constants,
                    get_gzip_url):
    ...
    expected = constants['GZIP_RESPONSE_TEXT'].encode()
    response = await asyncio.wait_for(one_time_session.get(get_gzip_url), timeout=3)
    assert 'content-encoding' in response.headers
    # then server sent encoded message!
    assert len(response.content) == len(expected)


@pytest.mark.asyncio
async def test_https_request(one_time_session):
    url = 'https://google.com'
    response = await one_time_session.get(url)
    assert response.status == 200


@pytest.mark.asyncio
async def test_dirctly_requests_using(one_time_session,
                                      event_loop):
    req = Request(
        url='https://google.com/',
        method='GET',
        headers={},
    )

    jsonreq = JsonRequest(
        url='https://google.com/',
        method='GET',
        headers={},
    )

    t1 = asyncio.create_task(one_time_session.send_request(req, redirect=0))
    t2 = asyncio.create_task(one_time_session.send_request(jsonreq, redirect=0))
    result1, result2 = await asyncio.gather(t1, t2)

    assert result1.status == 301 == result2.status
    assert 'content-type' in result1.headers


@pytest.mark.asyncio
async def test_stream_request(one_time_session_stream,
                              get_stream_test_url,
                              constants):
    t2 = bytearray()
    async for chunk in one_time_session_stream.get(get_stream_test_url):
        for byte in chunk:
            t2.append(byte)
    assert t2 == bytearray('test' * constants['STREAMING_RESPONSE_CHUNK_COUNT'], 'utf-8')


@pytest.mark.asyncio
async def test_root_with_stream(one_time_session_stream,
                                server):
    t2 = bytearray()
    async for chunk in one_time_session_stream.get(server):
        for byte in chunk:
            t2.append(byte)
    assert t2 == bytearray(b'"Hello World"')
