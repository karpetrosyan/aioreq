import aioreq
import asyncio

async def main():
    async with aioreq.http.Client() as cl:
        tasks = []
        for j in range(100):
            tasks.append(cl.get('https://www.google.com', retry=0, redirect=0))
        await asyncio.gather(*tasks)
asyncio.run(main())
