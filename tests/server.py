import asyncio
import sys
import zlib

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import PlainTextResponse, RedirectResponse, StreamingResponse
from starlette.routing import Route

from .conftest import CONSTANTS


async def startup():
    sys.stdout.write("started\n")
    sys.stdout.flush()


async def gzip(request):
    return PlainTextResponse(CONSTANTS["GZIP_RESPONSE_TEXT"])


async def deflate(request):
    compress = zlib.compressobj(
        9, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0
    )
    deflated = compress.compress(CONSTANTS["DEFLATE_RESPONSE_TEXT"].encode())
    deflated += compress.flush()
    return PlainTextResponse(content=deflated, headers={"content-encoding": "deflate"})


async def ping(request):
    return PlainTextResponse("pong")


async def redirect(request):
    return RedirectResponse(
        "/redirected", status_code=301
    )


async def redirected(request):
    return PlainTextResponse("200")


async def root(request):
    return PlainTextResponse("Hello World")


async def streaming_text():
    for i in range(CONSTANTS["STREAMING_RESPONSE_CHUNK_COUNT"]):
        yield b"test"
        await asyncio.sleep(0)


async def stream(request):
    return StreamingResponse(streaming_text())


async def set_cookie(request):
    resp = PlainTextResponse("200")
    resp.set_cookie(key="test", value="val")
    return resp


routes = [
    Route("/", root),
    Route("/ping", ping),
    Route("/gzip", gzip),
    Route("/deflate", deflate),
    Route("/redirect", redirect),
    Route("/redirected", redirected),
    Route("/test_stream", stream),
    Route("/set-cookie", set_cookie),
]

middlewares = [
    Middleware(
        GZipMiddleware
    )
]

app = Starlette(routes=routes,
                middleware=middlewares,
                on_startup=[startup])
