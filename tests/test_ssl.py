import tempfile

import pytest

import aioreq
from aioreq.connection import load_ssl_context


def test_load_context():
    with tempfile.NamedTemporaryFile() as tf:
        context = load_ssl_context(
            check_hostname=True, verify_mode=True, keylog_filename=tf.name
        )

        assert context.check_hostname
        assert context.verify_mode
        assert context.keylog_filename == tf.name


@pytest.mark.asyncio
async def test_keylog_filename():
    with tempfile.NamedTemporaryFile() as tf:
        keylog_filename = tf.name

        req = aioreq.Request(
            url="https://google.com/", method="GET", keylog_filename=keylog_filename
        )
        async with aioreq.Client() as client:
            resp = await client.send_request(req)
            assert resp.request.keylog_filename == keylog_filename
