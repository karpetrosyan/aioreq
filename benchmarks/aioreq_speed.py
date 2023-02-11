import asyncio
import sys
from time import perf_counter

import aioreq


async def main():
    async with aioreq.Client() as client:
        tasks = []
        for j in range(int(count)):
            tasks.append(client.get(url))
        t1 = perf_counter()
        await asyncio.gather(*tasks)
        time_spent = perf_counter() - t1
        text = f"Url: {url} | Requests: {count} | Time spent: {time_spent}"
        print(text)


if __name__ == "__main__":
    url, count = sys.argv[1:3]
    asyncio.run(main())
