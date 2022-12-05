import asyncio
import base64
import zlib

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from fastapi import Response

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.on_event('startup')
async def startup():
    print('started', flush=True)


@app.get("/gzip", response_class=Response)
async def gzip():
    return CONSTANTS['GZIP_RESPONSE_TEXT']


@app.get("/deflate")
async def deflate():
    string_val = CONSTANTS['DEFLATE_RESPONSE_TEXT']
    zlibbed_str = zlib.compress(string_val.encode())
    compressed_string = zlibbed_str[2:-4]
    return Response(content=base64.b64encode(compressed_string), headers={'content-encoding': 'deflate'})


@app.get('/ping')
async def ping():
    return 'pong'


@app.get('/redirect')
async def redirect():
    return Response(headers={'location': 'http://testulik.com/redirected'}, status_code=301)


@app.get('/redirected')
async def redirected():
    return 200


@app.get('/')
async def root():
    return "Hello World"


async def streaming_text():
    for i in range(CONSTANTS['STREAMING_RESPONSE_CHUNK_COUNT']):
        yield b'test'
        await asyncio.sleep(0)


@app.get('/test_stream')
async def stream():
    return StreamingResponse(streaming_text())


if __name__ == '__main__':
    from conftest import CONSTANTS
    import uvicorn

    uvicorn.run(app, port=7575)
else:
    from .conftest import CONSTANTS
