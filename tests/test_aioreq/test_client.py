import pytest
import asyncio
import aioreq
import pytest_asyncio

from aioreq.errors.requests import AsyncRequestsError

async def notworking_test_few_requests(one_time_session, event_loop):

    t1 = await one_time_session.get('https://www.facebook.com')
    t2 = await one_time_session.get('https://www.google.com')
    t3 = await one_time_session.get('https://www.youtube.com')
    await asyncio.gather(t1, t2, t3)
    assert t1.result().status == t2.result().status == t3.result().status

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


#@pytest.mark.asyncio
#async def test_same_domain_requests_with_cache_connections(one_time_session_cached,
#                                                           event_loop):
#   
#    loop = event_loop
#    t1 = loop.create_task(one_time_session_cached.get('https://www.youtube.com'))
#    t2 = loop.create_task(one_time_session_cached.get('https://www.youtube.com'))
#    await asyncio.gather(t1, t2)
#    print(t1, t2)
#



