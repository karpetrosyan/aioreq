**Aioreq** is a Python low-level asynchronous HTTP client library. It is built on top of TCP sockets and implements the HTTP protocol entirely on his own.

[mygit]: https://github.com/karosis88/aioreq

---

## Install
``` shell
$ pip install aioreq
```

## Usage
### Basic usage
---
``` python
>>> import aioreq
>>> import asyncio
>>>
>>> cl = aioreq.Client()
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

Alternatively, the best practice is to use a **Context manager**.
``` python
import aioreq
import asyncio

async def main():
        async with aioreq.Client() as cl:
                await cl.get('https://google.com')
```
### More advanced usage
---

This code will asynchronously send 100 get requests to [`google.com`](https://www.google.com), which is much faster than synchronous libraries.

``` python
>>> import asyncio
>>> import aioreq
>>>
>>> async def main():
>>>    async with aioreq.http.Client() as cl:
>>>        tasks = []
>>>        for j in range(100):
>>>            tasks.append(
>>>		                  asyncio.create_task(
>>>		  	                  cl.get('https://www.google.com/', )
>>>				                 )
>>> 			           )
>>>        await asyncio.gather(*tasks)
>>>
>>> asyncio.run(main())
```

### Streams
---
We occasionally use the HTTP protocol to download videos, photos, and possibly files. When downloading very large files, Stream must be used instead of the default Client. When a client downloads videos or files, the server responds with all information including headers, status code, status message, and full body, which can be very large. As a result, we cannot store it in RAM. Stream only returns a portion of the body per iteration, allowing us to write it to disk, then receive another portion and solve the ram overflow problem.

There is some fundamental Stream usage.
``` python
>>> import aioreq
>>> import asyncio
>>> 
>>> async def main():
>>>        local_file = open('test', 'wb')
>>>        async with aioreq.StreamClient() as cl:
>>>                # This code iterates through the message and yields each received chunk separately.
>>>                async for chunk in cl.get('https://pathtoverybigfile.aioreq'):
>>>                        local_file.write(chunk)


```

## Benchmarks
**Aioreq** is a very fast library, and we compared it to other Python libraries to demonstrate its speed.




I used these libraries to compare speed.
* [httpx](https://github.com/encode/httpx)
* [requests](https://github.com/psf/requests)
---
### Benchmark run

First, clone aioreq [repository][mygit].

Then...

```shell
$ cd aioreq
$ python -m venv venv
$ source ./venv/bin/activate
$ pip install '.[benchmarks]'
$ cd benchmarks
$ python run_tests_functions.py
```
---
### Benchmark results

This is the **average** execution time of each library for **200 asynchronous requests** where responses was received without **chunked** transfer encoding.
<br/>


Benchmark settings.

* **Url** - https://www.github.com
* **Requests count** - 200 for async and 5 for sync libs

#### With `Content-Length`
``` shell
$ cd becnhmarks
$ python run_tests_functions.py
========================
Benchmark settings
        Async lib test requests count : 200
        Sync lib test requests count  : 5
=======================
Function test for aioreq completed. Total time: 1.2442591340004583
Received statuses
        {301: 200}
Function test for requests completed. Total time: 1.6835168350007734
Received statuses
        {200: 5}
Function test for httpx completed. Total time: 1.691718664000291
Received statuses
        {301: 200}
```

#### With `Transfer-Encoding: Chunked`
This is the **average** execution time of each library for **100 asynchronous requests** where responses was received with **chunked** transfer encoding.
<br/>

Benchmark settings.

* **Url** - https://www.youtube.com
* **Requests count** - 100 for async and 5 for sync libs

```shell
$ cd benchmarks
$ python run_tests_functions.py
========================
Benchmark settings
        Async lib test requests count : 100
        Sync lib test requests count  : 5
=======================
Function test for aioreq completed. Total time: 3.837283965000097
Received statuses
        {200: 100}
Function test for requests completed. Total time: 6.098562907998712
Received statuses
        {200: 5}
Function test for httpx completed. Total time: 6.467480723000335
Received statuses
        {200: 100}
```

As you can see, the synchronous code lags far behind when we make many requests at the same time.<br />

## Supported Features
**Aioreq** support basic features to work with **HTTP/1.1**.<br />More functionality will be avaliable in future realeases.<br />
This is the latest version features.
* Keep-Alive (Persistent Connections)
* Automatic accepting and decoding responses. Using `Accept-Encoding` header
* HTTPS support, TLS/SSL Verification using [certifi](https://github.com/certifi/python-certifi) library
* Request Timeouts

