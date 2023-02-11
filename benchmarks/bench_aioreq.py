import asyncio

from benchmark_settings import REQUESTS_COUNT
from benchmark_settings import REQUESTS_URL

import aioreq


async def send_req(cl):
    resp = await cl.get(REQUESTS_URL)
    return resp.status


async def main():
    async with aioreq.http.Client() as cl:
        tasks = []
        for j in range(REQUESTS_COUNT):
            tasks.append(send_req(cl))
        a = await asyncio.gather(*tasks)
        print(a)
        return a


if __name__ == "__main__":
    asyncio.run(main())
