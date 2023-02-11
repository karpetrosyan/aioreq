import pytest

from aioreq.urls import parse_url


@pytest.mark.asyncio
async def test_persistent_connections_base(temp_session_cached, SERVER_URL):
    parsed = parse_url(SERVER_URL)
    domain = parsed.get_domain()
    await temp_session_cached.get(SERVER_URL)
    assert len(temp_session_cached.connection_mapper[domain]) == 1
    old_transport = temp_session_cached.connection_mapper[domain][0]

    await temp_session_cached.get(SERVER_URL)

    if not old_transport.is_closing():
        assert old_transport is temp_session_cached.connection_mapper[domain][0]
    else:
        assert len(temp_session_cached.connection_mapper[domain]) == 1
