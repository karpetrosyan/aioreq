import logging

from ..settings import BUFFER_SIZE
from collections import deque

log = logging.getLogger('aioreq')

class Queue:

    def __init__(self, iterable = None):

        if iterable is None:
            iterable = ()
        self._queue = deque(iterable)

    def append(self, value):
        self._queue.appendleft(value)
        return value

    def pop(self):
        return self._queue.pop()

class Buffer:
    """
    Buffer class which gives default interface for working with bytearray

    This class used to store bytes becoming from a TCP transport which
    used for HTTP protocol implementation, gives base interface to store and get 
    bytes from the bytearray with default size specified in the settings.BUFFER_SIZE
    """

    def __init__(self):
        """
        Initalization for Buffer
        """

        self.data = bytearray(BUFFER_SIZE)
        self.current_point = 0
        self.unique_id = 0
        self.queue = Queue()

    def get_id(self):
        id = self.unique_id
        self.unique_id += 1
        return id

    def clear_id(self):
        self.unique_id = 0


    async def my_turn_to_add(self, unique_id, data_len):
        while self.queue[-1][1] != unique_id or (not await self.buffer_freeing(data_len)):
            await asyncio.sleep(0)
        self.queue.pop()
        return

    async def add_bytes(self, data: bytes):
        """
        Adding bytes into the buffer

        :param data: data which should be added into buffer
        :type data: bytearray
        :returns: None
        """
        unique_id = self.get_id()

        data_len = len(data)
        await self.my_turn_to_add(unique_id, data_len)
        assert BUFFER_SIZE - self.current_point >= data_len
        self.data[self.current_point:self.current_point+data_len] = data
        self += data_len
    
    async def buffer_freeing(self, bytes_count) -> None:
        """
        Method which waits until bytes_count can be stroed in the buffer

        :param bytes_count: size of bytes which should be stored
        :type bytes_count: int
        :returns: None
        """
        while BUFFER_SIZE - self.current_point < bytes_count:
            await asyncio.sleep(0)

    async def left_add_bytes(self, bytes) -> None:
        """
        Adding bytes from left size, works like appendleft for dequeue

        :param bytes: bytes that shoule be added into the buffer
        :type bytes: bytearray
        :returns: None
        """

        bytes_count = len(bytes)
        await self.buffer_freeing(bytes_count)
        assert BUFFER_SIZE - self.current_point >= bytes_count 
        self.data[bytes_count:self.current_point + bytes_count] = self.data[:self.current_point]
        self += bytes_count
        self.data[:bytes_count] = bytes

    def get_data(self, bytes_count = None):
        """
        Getting data from the buffer

        Getting and decoding buffer data, also decreasing self.current_point
        which references to the first free byte in our buffer

        :returns: decoded data from buffer
        :rtype: str
        """

        if not bytes_count:
            bytes_count = self.current_point

        decoded_data = self.data[:bytes_count].decode('utf-8')
        self.data[:self.current_point] = (0, ) * self.current_point
        self.current_point = 0
        return decoded_data

    def clean(self):
        
        self.data[:self.current_point] = (0,) * self.current_point
        self.current_point = 0

    def __iadd__(self, bytes_count):
        """
        Overloaded += operator for buffer object

        Increasing buffer self.current_point value with 'bytes_count' variable  
        """

        self.current_point += bytes_count
        return self

    def __isub__(self, bytes_count):
        """
        Overloaded -= operator for buffer object

        Decreasing buffer self.current_point value with 'bytes_count' variable  
        """

        self.current_point -= bytes_count
        return self

class HttpBuffer(Buffer):
    ...

        
        

