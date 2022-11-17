import asyncio

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from .conftest import CONSTANTS

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.on_event('startup')
async def startup():
    print('started', flush=True)

@app.get("/gzip")
async def gzip():
    return CONSTANTS['GZIP_RESPONSE_TEXT']

@app.get('/ping')
async def ping():
    return 'pong'


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
