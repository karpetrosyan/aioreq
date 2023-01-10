import httpx
import asyncio

from benchmark_settings import REQUESTS_COUNT
from benchmark_settings import REQUESTS_URL


async def send_req(cl):
    resp = await cl.get(REQUESTS_URL)
    return resp.status_code


async def main():
    async with httpx.AsyncClient(follow_redirects=True) as cl:
        tasks = []
        for j in range(REQUESTS_COUNT):
            tasks.append(send_req(cl, ))
        a = await asyncio.gather(*tasks)
        print(a)
        return a


if __name__ == '__main__':
    asyncio.run(main())
