from fastapi import FastAPI
from fastapi import APIRouter
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()
router = APIRouter()
app.add_middleware(GZipMiddleware, minimum_size=1000)
router.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/")
async def main():
    return "somebigcontent" * 1000000
