import pytest

from aioreq.parser.url_parser import parse_url


@pytest.mark.asyncio
async def test_persistent_connections_base(one_time_session_cached, event_loop):
    url = "https://www.google.com"
    parsed = parse_url(url)
    domain = parsed.get_domain()
    await one_time_session_cached.get(url)
    assert len(one_time_session_cached.connection_mapper[domain]) == 1
    old_transport = one_time_session_cached.connection_mapper[domain][0]

    await one_time_session_cached.get(url)

    if not old_transport.is_closing():
        assert (
            old_transport is one_time_session_cached.connection_mapper[domain][0]
        )
    else:
        assert len(one_time_session_cached.connection_mapper[domain]) == 1
