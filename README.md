**Aioreq** is a low level asynchronous HTTP client library for Python. It's built on top of non-blocking TCP sockets.

[mygit]: https://github.com//aioreq

---

## Install
``` shell
$ pip install aioreq
```

## Usage
### Basic usage

``` python
>>> import aioreq
>>> import asyncio
>>>
>>> cl = aioreq.http.Client()
>>>
>>> resp = asyncio.run(
>>>	cl.get('https://www.google.com')
>>>	)
>>> resp
<Response 200 OK>
>>> resp.status
200
>>> resp.status_message
'OK'
>>> resp.request
<Request GET https://www.google.com>
>>> headers = resp.headers # dict
>>> body = resp.body # bytes object
```
### More advanced usage

This code will send 100 get requests to [`google.com`](https://www.google.com) asynchronously which is much faster then sync requests like [requests](https://github.com/psf/requests) library do.

``` python
>>> import asyncio
>>> import aioreq
>>>
>>> async def main():
>>>    cl = aioreq.http.Client()
>>>    tasks = []
>>>    for j in range(100):
>>>        tasks.append(
>>>		asyncio.create_task(
>>>			cl.get('https://www.youtube.com/', )
>>>				)
>>> 			)
>>>    await asyncio.gather(*tasks)
>>>
>>> asyncio.run(main())
```
## Benchmarks
**Aioreq** is a really fast library and to demonstrate the speed, we compared the same program with different python libraries.




Libraries that i used to compare speed.
* [aiohttp](https://github.com/aio-libs/aiohttp)
* [httpx](https://github.com/encode/httpx)
* [requests](https://github.com/psf/requests)
---
### Benchmark run

Clone aioreq [repository][mygit] for first.

Then...

```shell
$ cd aioreq
$ python -m venv venv
$ source ./venv/bin/activate
$ pip install '.[benchmarks]'
$ cd benchmarks
$ source run_tests
```
---
### Benchmark results

This is the **average** execution time of each library for **300 asynchronous requests** where responses was received without **chunked** transfer encoding.
<br/>


Benchmark settings.

* **Url** - https://www.google.com
* **Requests count** - 300

#### With `Content-Length`
``` shell
$ cd benchmarks
$ source run_tests
Tests with module loading
---------------------------
aiohttp benchmark

real    0m3.644s
user    0m1.179s
sys     0m0.193s
---------------------------
aioreq benchmark

real    0m1.808s
user    0m0.505s
sys     0m0.096s
---------------------------
httpx benchmark

real    0m3.965s
user    0m1.699s
sys     0m0.263s
---------------------------
requests benchmark (only 5 requests)

real    0m4.075s
user    0m0.220s
sys     0m0.016s
```

#### With `Transfer-Encoding: Chunked`
This is the **average** execution time of each library for **50 asynchronous requests** where responses was received with **chunked** transfer encoding.
<br/>

Benchmark settings.

* **Url** - https://www.youtube.com
* **Requests count** - 50

```shell
$ cd benchmarks
$ source run_tests
Tests with module loading
---------------------------
aiohttp benchmark

real    0m1.821s
user    0m0.475s
sys     0m0.123s
---------------------------
aioreq benchmark

real    0m2.100s
user    0m0.832s
sys     0m0.068s
---------------------------
httpx benchmark

real    0m2.289s
user    0m1.188s
sys     0m0.192s
---------------------------
requests benchmark (only 5 requests)

real    0m4.508s
user    0m0.289s
sys     0m0.029s
```

As you can see, the synchronous code lags far behind when we make many requests at the same time.<br />



These tests are made for **Python 3.11**, for versions **<=3.11** aioreq will run **little bit slower**, since optimizations have been added to python 3.11 that **greatly affect** aioreq.



## Supported Features
**Aioreq** support basic features to work with **HTTP/1.1**.<br />More functionality will be avaliable in future realeases.<br />
This is the latest version features.
* Keep-Alive (Persistent Connections)
* Automatic accepting and decoding responses. Using `Accept-Encoding` header
* HTTPS support, TLS/SSL Verification using [certifi](https://github.com/certifi/python-certifi) library
* Request Timeouts

