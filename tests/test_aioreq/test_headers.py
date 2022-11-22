from aioreq.protocol.http import HeaderDict


def test_HeaderDict_base():
    headers = HeaderDict(initial_headers={'content-LEngth': '200'})
    assert headers.get('content-lEngth') == '200'
    assert len(headers) == 1
    assert 'content-length' in headers._headers


def test_header_override():
    headers = HeaderDict()

    headers['Transfer-Encoding'] = 'chunked'
    headers['Transfer-eNCoding'] = 'gzip'

    assert headers['Transfer-Encoding'] == 'gzip'
    assert 'Transfer-Encoding' in headers
    assert 'transFER-encoding' in headers
