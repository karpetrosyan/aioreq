import asyncio
import pytest
import aioreq


@pytest.fixture(scope='session')
async def session():
    with aioreq.http.Client() as s:
        yield s

async def test_moved_301(session):
    url = 'http://google.com'
    response = await session.get(url)
    assert response.status_code == 301
    


