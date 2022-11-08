import aioreq
import asyncio

from benchmark_settings import REQUESTS_COUNT
from benchmark_settings import REQUESTS_URL

async def main():
    async with aioreq.http.Client() as cl:
        tasks = []
        for j in range(REQUESTS_COUNT):
            tasks.append(cl.get(REQUESTS_URL, retry=0, redirect=0))
        await asyncio.gather(*tasks)
        
if __name__ == '__main__':
    asyncio.run(main())