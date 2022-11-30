import asyncio
import logging

from time import time
from time import perf_counter

from bench_test_aioreq import main as aioreq_main
from bench_test_httpx import main as httpx_main
from bench_test_requests import main as requests_main
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from benchmark_settings import REQUESTS_COUNT
from benchmark_settings import SYNC_REQUESTS_COUNT


lock = Lock()

text = ('========================\n'
        'Benchmark settings\n'
        f'\tAsync lib test requests count : {REQUESTS_COUNT}\n'
        f'\tSync lib test requests count  : {SYNC_REQUESTS_COUNT}\n'
        f'=======================')

print(text)


def print_result(text):
    with lock:
        print(text)


def run_benchmark_async(benchmark_name, function):
    try:
        loop = asyncio.new_event_loop()
        t1 = perf_counter()
        responses = loop.run_until_complete(function())
        t2 = perf_counter()
        codes = {}
        for code in responses:
            if code not in codes:
                codes[code] = 0
            codes[code] += 1

        print_result(
            (f"Function test for {benchmark_name} completed. Total time: {t2 - t1}\n"
             f"Received statuses\n"
             f"\t{codes}"
             )
        )
    except BaseException as e:
        print_result(f"Error: {e} type of {type(e)} was raised for {benchmark_name}")


def run_benchmark_sync(benchmark_name, function):
    try:
        t1 = perf_counter()
        responses = function()
        t2 = perf_counter()
        codes = {}
        for code in responses:
            if code not in codes:
                codes[code] = 0
            codes[code] += 1
        print_result(
            (f"Function test for {benchmark_name} completed. Total time: {t2 - t1}\n"
             f"Received statuses\n"
             f"\t{codes}"
             )
        )
    except BaseException as e:
        print_result(f"Error: {e} type of {type(e)} was raised for {benchmark_name}")


async_test_configs = {

    aioreq_main: {
        'benchmark_name': 'aioreq',
        'function': run_benchmark_async
    },
    httpx_main: {
        'benchmark_name': 'httpx',
        'function': run_benchmark_async
    },
    requests_main: {
        'benchmark_name': 'requests',
        'function': run_benchmark_sync
    }
}

if __name__ == '__main__':
    with ThreadPoolExecutor(6) as pool:
        pool.map(
            lambda md: async_test_configs[md]['function'](
                benchmark_name=async_test_configs[md]['benchmark_name'],
                function=md
            ),
            (requests_main, aioreq_main, httpx_main)
        )
