import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as cl:
        tasks = []
        for j in range(100):
            tasks.append(cl.get('https://youtube.com', ))
        await asyncio.gather(*tasks)
asyncio.run(main())
