**Aioreq** is a low level asynchronous HTTP client library for Python. It's built on top of non-blocking TCP sockets.

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

or using **Context manager** which is the best practice.
``` python
import aioreq
import asyncio

async def main():
        async with aioreq.Client() as cl:
                await cl.get('https://google.com')
```
### More advanced usage
---

This code will send 100 get requests to [`google.com`](https://www.google.com) asynchronously which is much faster then sync requests like [requests](https://github.com/psf/requests) library do.

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
Sometimes we use HTTP protocol to download videos, photos and maybe some files. When downloading  very large files, it is necessary to use Stream instead of the default Client. A client gives us a response which contains all information including headers, status code, status message and full body, which can be very large when it downloads videos or files. So we can't store it in RAM. Stream gives just a chunk of the body each time, so we can write it onto the hard drive, then receive another chunk and solve the ram overflow problem.

There is some basic Stream usage
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
**Aioreq** is a really fast library and to demonstrate the speed, we compared the same program with different python libraries.




Libraries that i used to compare speed.
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

