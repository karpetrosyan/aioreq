import aiohttp
import asyncio

from benchmark_settings import REQUESTS_COUNT
from benchmark_settings import REQUESTS_URL

async def main():
    async with aiohttp.ClientSession() as cl:
        tasks = []
        for j in range(REQUESTS_COUNT):
            tasks.append(cl.get(REQUESTS_URL))
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
