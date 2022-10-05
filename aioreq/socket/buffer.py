import logging

from ..settings import BUFFER_SIZE

log = logging.getLogger('aioreq')

class Buffer:

    def __init__(self):
        self.data = bytearray(BUFFER_SIZE)
        self.current_point = 0

    async def add_bytes(self, data: bytes):
        data_len = len(data)
        log.debug(f"Trying to add data with {data_len=}")
        await self.buffer_freeing(data_len)
        assert BUFFER_SIZE - self.current_point >= data_len
        log.debug(f"Buffer pointer before adding new data {self.current_point=}")
        self.data[self.current_point:self.current_point+data_len] = data
        log.debug(f"Buffer pointer after adding new data {self.current_point=}")
        self += data_len
    
    async def buffer_freeing(self, bytes_count):
        while BUFFER_SIZE - self.current_point < bytes_count:
            await asyncio.sleep(0)
        return True

    def __iadd__(self, bytes_count):
        self.current_point += bytes_count

    def __isub__(self, bytes_count):
        self.current_point -= bytes_count
        
        

