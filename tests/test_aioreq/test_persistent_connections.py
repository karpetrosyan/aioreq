import pytest

from aioreq.parser.url_parser import parse_url


@pytest.mark.asyncio
async def test_persistent_connections_base(temp_session_cached, server):
    url = server
    parsed = parse_url(url)
    domain = parsed.get_domain()
    await temp_session_cached.get(url)
    assert len(temp_session_cached.connection_mapper[domain]) == 1
    old_transport = temp_session_cached.connection_mapper[domain][0]

    await temp_session_cached.get(url)

    if not old_transport.is_closing():
        assert (
            old_transport is temp_session_cached.connection_mapper[domain][0]
        )
    else:
        assert len(temp_session_cached.connection_mapper[domain]) == 1
