import asyncio

import pytest

from aioreq import AsyncRequestsError, UrlParser


@pytest.mark.asyncio
async def test_persistent_connections_base(one_time_session_cached,
                                            event_loop):
    url = 'https://www.github.com'
    splited_url = UrlParser.parse(url)
    url_for_dns = splited_url.get_url_for_dns()
    await one_time_session_cached.get(url)
    assert len(one_time_session_cached.connection_mapper[url_for_dns]) == 1
    old_transport = one_time_session_cached.connection_mapper[url_for_dns][0]

    await one_time_session_cached.get(url)

    if not old_transport.is_closing():
        assert old_transport is one_time_session_cached.connection_mapper[url_for_dns][0]
    else:
        assert len(one_time_session_cached.connection_mapper[url_for_dns]) == 1


