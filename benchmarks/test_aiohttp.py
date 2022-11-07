import aiohttp
import asyncio

async def main():
    async with aiohttp.ClientSession() as cl:
        tasks = []
        for j in range(100):
            tasks.append(cl.get("https://www.google.com"))
        await asyncio.gather(*tasks)
asyncio.run(main())
