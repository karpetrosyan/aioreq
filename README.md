**Aioreq** is a low level asynchronous HTTP client library for Python. It's built on top of non-blocking TCP sockets.

[mygit]: https://github.com//aioreq

---

## Install
```shell
$ pip install aioreq
```

## Usage
### Basic usage

```pycon
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

This code will send 100 get requests to `google.com` asynchronously which is much faster then sync requests like [requests](https://github.com/psf/requests) library do.

```
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

Libraries were specified after the prefix \`bench\_test\_\`.

```shell
$ cd benchmarks
$ source run_tests
python test_aiohttp.py  2.01s user 0.25s system 62% cpu 3.599 total
python test_aioreq.py  2.11s user 0.19s system 70% cpu 3.274 total
python test_httpx.py  2.90s user 0.39s system 85% cpu 3.849 total
python test_requests.py  1.74s user 0.13s system 2% cpu 1:15.40 total
```

As you can see, the synchronous code lags far behind when we make many requests at the same time.<br />
And the **fastest** asynchronous client turned out to be **aioreq**.<br/>
<br/>
This is the **average** execution time of each library for **100 asynchronous requests** where responses was received with **Chunked** transfer encoding.
<br/>
<br/>
These tests are made for **Python 3.11**, for versions **<=3.11** aioreq will run **much slower**, since optimizations have been added to python 3.11 that **greatly affect** aioreq.

## Supported Features
**Aioreq** support basic features to work with **HTTP/1.1**.<br />More functionality will be avaliable in future realeases.<br />
This is the latest version features.
* Keep-Alive (Persistent Connections)
* Automatic accepting and decoding responses. Using `Accept-Encoding` header
* HTTPS support, TLS/SSL Verification using [certifi](https://github.com/certifi/python-certifi) library
* Request Timeouts

