import pytest
import asyncio
import aioreq
import pytest_asyncio

from aioreq.errors.requests import AsyncRequestsError

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
    assert response.status == 301

@pytest.mark.asyncio
async def test_moving_301(one_time_session):
    url = 'http://google.com'
    response = await one_time_session.get(url, retry=0, redirect=1)
    assert response.status == 200

@pytest.mark.asyncio
async def test_https_request(one_time_session):
    url = 'https://google.com'
    response = await one_time_session.get(url)
    assert response.status == 200

@pytest.mark.asyncio
async def test_gzip_request(one_time_session,
                            get_gzip_url):
    expected = ('testgzip' * 100000).encode()
    response = await one_time_session.get(get_gzip_url)
    assert 'content-encoding' in response.headers # if content-encoding exists
                                                  # then server sent encoded message!
    assert len(response.body) == len(expected)

@pytest.mark.asyncio
async def test_ping(one_time_session,
                    server):
    response = await one_time_session.get(server)
    assert response.status == 200

@pytest.mark.asyncio
async def test_same_domain_requests_with_cache_connections(one_time_session_cached,
                                                           event_loop):
    
    with pytest.raises(AsyncRequestsError):
        loop = event_loop
        t1 = loop.create_task(one_time_session_cached.get('https://www.youtube.com'))
        t2 = loop.create_task(one_time_session_cached.get('https://www.youtube.com'))
        results = await asyncio.gather(t1, t2, return_exceptions = True)
        for result in results:
            if isinstance(result, Exception):
                raise result
        





