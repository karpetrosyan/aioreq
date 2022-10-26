from fastapi import FastAPI
from fastapi import APIRouter
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/gzip")
async def gzip():
    return "somebigcontent" * 1000000

@app.get('/ping')
async def ping():
    return 'pong'

@app.get('/')
async def root():
    return "Hello World"
