import aioreq


async def main():
    async with aioreq.Client() as cl:
        response = await cl.get("https://www.google.com", stream=True)
        async for chunk in response.stream.read_by_chunks(2000):
            print(chunk)


import asyncio

asyncio.run(main())

import requests

resp = requests.get("https://www.google.com", stream=True)
