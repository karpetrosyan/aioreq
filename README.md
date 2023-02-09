**Aioreq** is a Python low-level asynchronous HTTP client library. It is built on top of TCP sockets and implements the HTTP protocol entirely on his own.

[mygit]: https://github.com/karosis88/aioreq
[documentation]: https://karosis88.github.io/aioreq/

---

## Documentation
[Click here][documentation]

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
...	cl.get('https://www.google.com')
...	)
>>> resp
<Response 200 OK>
>>> resp.status
200
>>> resp.status_message
'OK'
>>> resp.request
<Request GET www.google.com>
>>> headers = resp.headers # dict
>>> body = resp.content # bytes object

```

or you can use the default client, which is a synchoronous wrapper for an asynchronous interface

``` python
>>> aioreq.get('https://www.google.com')
<Response 200 OK>

```

Alternatively, the best practice is to use a **Context manager**.
``` python
>>> import aioreq
>>> import asyncio
>>>
>>> async def main():
...     async with aioreq.Client() as cl:
...         return await cl.get('https://google.com')
>>> asyncio.run(main())
<Response 200 OK>

```

### More advanced usage
---

This code will asynchronously send 100 get requests to [`google.com`](https://www.google.com), which is much faster than synchronous libraries.
Also, the client persistent connection mechanism was disabled, so that a connection would be opened for each request.

``` python
>>> import asyncio
>>> import aioreq
>>>
>>> async def main():
...     async with aioreq.http.Client(persistent_connections=False) as cl:
...         tasks = []
...         for j in range(100):
...             tasks.append(
...                 asyncio.create_task(
...                     cl.get('https://www.google.com/', )
...                 )
...             )
...         await asyncio.gather(*tasks)
>>> asyncio.run(main())

```

### Streams
---
We occasionally use the HTTP protocol to download videos, photos, and possibly files. When downloading very large files, Stream must be used instead of the default Client. When a client downloads videos or files, the server responds with all information including headers, status code, status message, and full body, which can be very large. As a result, we cannot store it in RAM. Stream only returns a portion of the body per iteration, allowing us to write it to disk, then receive another portion and solve the ram overflow problem.

There is some fundamental Stream usage.
``` python
>>> import aioreq
>>> import asyncio
>>> from aioreq import Request
>>> 
>>> async def main():
...     req = Request(url="https://www.youtube.com", method="GET")
...     async with aioreq.StreamClient(request=req) as response:
...         assert response.status == 200
...         async for chunk in response.content:
...             assert chunk   
>>> asyncio.run(main())

```

## Middlewares
**Aioreq** now supports 'middleware' power.

### The first steps with middleware

Aioreq provides default middlewares to each client.
We can see that middlewares by importing 'default_middlewares'  variable.
``` python
>>> import aioreq
>>> aioreq.middlewares.default_middlewares
('RetryMiddleWare', 'RedirectMiddleWare', 'CookiesMiddleWare', 'DecodeMiddleWare', 'AuthenticationMiddleWare')

```
The first item on this list represents the first middleware that should handle our request (i.e. the closest middleware to our client), while the last index represents the closest middleware to the server.


To override the default middlewares, we can pass our middlewares to the Client.
``` python
>>> client = aioreq.Client(middlewares=aioreq.middlewares.default_middlewares[2:])

```

This client will no longer redirect or retry responses.

Also, because aioreq stores middlewares in Client objects as linked lists, we can simply change the head of that linked list to skip the first middleware.
``` python
>>> client = aioreq.Client()
>>> client.middlewares.__class__.__name__
'RetryMiddleWare'
>>>
>>> client.middlewares = client.middlewares.next_middleware
>>> client.middlewares.__class__.__name__
'RedirectMiddleWare'
>>> 
>>> client.middlewares = client.middlewares.next_middleware
>>> client.middlewares.__class__.__name__
'CookiesMiddleWare'

```

or 
``` python
>>> client = aioreq.Client()
>>> client.middlewares = client.middlewares.next_middleware.next_middleware
>>> # alternative for client = aioreq.Client(middlewares=aioreq.middlewares.default_middlewares[2:])

```

### Create your own middlewares!

All 'aioreq' middlewares must be subclasses of the class 'middlewares.MiddleWare'

MiddleWare below would add 'test-md' header if request domain is 'www.example.com'
``` python
>>> import aioreq
>>>
>>> class CustomMiddleWare(aioreq.middlewares.MiddleWare):
...     async def process(self, request, client):
...         if request.host == 'www.example.com':
...             request.headers['test_md'] = 'test'
...         return await self.next_middleware.process(request, client)
...
>>> client = aioreq.Client()
>>> client.middlewares = CustomMiddleWare(next_middleware=client.middlewares)

```
Our CustomMiddleWare will now be the first middleware (i.e. closest to the client). Because 'aioreq' middlewares are stored as linked lists, this pattern works (i.e. same as linked list insert method).

Alternatively, we can alter the list of middlewares that the client receives.
``` python
>>> client = aioreq.Client(middlewares = (CustomMiddleWare, ) + aioreq.middlewares.default_middlewares)
>>> client.middlewares.__class__.__name__
'CustomMiddleWare'

```


## Benchmarks
**Aioreq** is a very fast library, and we compared it to other Python libraries to demonstrate its speed.




I used [httpx](https://github.com/encode/httpx) to compare speed.

---
### Benchmark run

First, clone aioreq [repository][mygit].

Then...

``` shell
$ cd aioreq
$ python -m venv venv
$ source ./venv/bin/activate
$ pip install '.[dev]'
$ cd benchmarks
$ ./run_tests
```

---

### Benchmark results

This is the **average** execution time of each library for **200 asynchronous requests** where responses was received without **chunked** transfer encoding.
<br/>


Benchmark settings.

* **Url** - http://www.google.com
* **Requests count** - 200
#### With `Content-Length`
``` shell
$ cd becnhmarks
$ ./run_tests
Tests with module loading
---------------------------
aioreq benchmark

real    0m1.893s
user    0m0.777s
sys     0m0.063s
---------------------------
httpx benchmark

real    0m2.448s
user    0m0.840s
sys     0m0.151s
```

#### With `Transfer-Encoding: Chunked`
This is the **average** execution time of each library for **200 asynchronous requests** where responses was received with **chunked** transfer encoding.
<br/>

Benchmark settings.

* **Url** - https://www.youtube.com
* **Requests count** - 200

```shell
$ cd benchmarks
$ ./run_tests
Tests with module loading
---------------------------
aioreq benchmark

real    0m2.444s
user    0m1.090s
sys     0m0.089s
---------------------------
httpx benchmark

real    0m2.990s
user    0m1.254s
sys     0m0.127s
```

As you can see, the synchronous code lags far behind when we make many requests at the same time.<br />

## Keylog

If the **SSLKEYLOGFILE** environment variable is set, Aioreq will write keylogs to it.

``` shell
$ export SSLKEYLOGFILE=logs
```

Then just run python script.

``` shell
$ python aioreq_app.py
$ ls -l
total 8
-rw-r--r-- 1 user user  94 Dec  5 17:19 aioreq_app.py
-rw-r--r-- 1 user user 406 Dec  5 17:19 logs
```
Now, the 'logs' file contains keylogs that can be used to decrypt your TLS/SSL traffic with a tool such as 'wireshark'.

## Authentication

If the `auth` parameter is included in the request, Aioreq will handle authentication.
``` python
>>> import aioreq
>>> import asyncio
>>> async def send_req():
...     async with aioreq.Client() as cl:
...         return await cl.get('http://httpbin.org/basic-auth/foo/bar', auth=('foo', 'bar'))
>>> resp = asyncio.run(send_req())
>>> resp.status
200

```
Parameter 'auth' should be a tuple with two elements: password and login.

Authentication is enabled by 'AuthenticationMiddleWare,' so exercise caution when managing middlewares manually.


## Supported Features
**Aioreq** support basic features to work with **HTTP/1.1**.<br />More functionality will be available in future releases.<br />
This is the latest version features.

* [Keep-Alive (Persistent Connections)](#more-advanced-usage)
* [Middlewares](#middlewares)
* [Keylogs](#keylog)
* [Authentication](#authentication)
* Cookies
* Automatic accepting and decoding responses. Using `Accept-Encoding` header
* HTTPS support, TLS/SSL Verification
* Request Timeouts
