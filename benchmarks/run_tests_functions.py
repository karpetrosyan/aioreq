import asyncio

from time import time
from time import perf_counter

from bench_test_aiohttp import main as aiohttp_main
from bench_test_aioreq import main as aioreq_main
from bench_test_httpx import main as httpx_main
from bench_test_requests import main as requests_main
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

lock = Lock()


def print_result(text):
    with lock:
        print(text)

def run_benchmark_async(benchmark_name, function):
    print('Run benchmark...')
    loop = asyncio.new_event_loop()
    t1 = perf_counter()
    loop.run_until_complete(function())
    t2 = perf_counter()
    print_result(f"Function test for {benchmark_name} completed. Time spent: {t2-t1}")

def run_benchmark_sync(benchmark_name, function):
    print('Run benchmark...')
    t1 = perf_counter()
    function()
    t2 = perf_counter()
    print_result(f"Function test for {benchmark_name} completed. Time spent: {t2-t1}")

async_test_configs = {
    aiohttp_main : {
        'benchmark_name' : 'aiohttp',
        'function' : run_benchmark_async
    },
    aioreq_main : {
        'benchmark_name' : 'aioreq',
        'function' : run_benchmark_async
    },
    httpx_main : {
        'benchmark_name' : 'httpx',
        'function' : run_benchmark_async
    },
    requests_main : {
        'benchmark_name' : 'requests',
        'function' : run_benchmark_sync
    }
}


if __name__ == '__main__':
    with ThreadPoolExecutor(6) as pool:
        pool.map(
            lambda md: async_test_configs[md]['function'](
                benchmark_name = async_test_configs[md]['benchmark_name'],
                function = md
            ),  
            (requests_main, aiohttp_main, aioreq_main, httpx_main)
            )
      
        

