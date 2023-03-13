<p align="center">
    <img style="width:300px" src="https://raw.githubusercontent.com/karosis88/aioreq/b9a4fa392798c49f2eb533ffb60b8c5564524f72/.github/images/logo.svg"></img>
</p>

<p align="center">
    <b>Aioreq</b> is a Python asynchronous HTTP client library. It is built on top of TCP sockets and implements the HTTP protocol entirely on his own.
</p>

[mygit]: https://github.com/karosis88/aioreq
[documentation]: https://karosis88.github.io/aioreq/

---

## Documentation
[Click here][documentation]

## Install

From [pypi](https://pypi.org/)
``` shell
$ pip install aioreq
```

From [GitHub][mygit]
``` shell
$ git clone https://github.com/karosis88/aioreq
$ pip install ./aioreq
```

`Aioreq` can be used as a Python library or as a command-line tool to make HTTP requests.

## Basic Usage

### Python
``` pycon
>>> import aioreq
>>> response = aioreq.get("http://127.0.0.1:7575/")
>>> response.status
200
>>> content_type = response.headers["content-type"] # Case insensitive
>>> response.content
b'Hello World'

```

or in async context

``` pycon
>>> import asyncio
>>> 
>>> async def main():
...     async with aioreq.Client() as client:
...         response = await client.get("http://127.0.0.1:7575")
...         return response
>>> asyncio.run(main())
<Response 200 OK>

```

### CLI
`Aioreq` cli tools are very similar to [curl](https://github.com/curl/curl), so if you've used curl before, you should have no trouble.

``` shell
$ aioreq http://127.0.0.1:7575/cli_doc
Hello World
```


When performing HTTP requests, there are a few options available.

* `--method -X` Specify HTTP method
* `--verbose -v` Show HTTP request headers
* `--include -i` Include HTTP response headers
* `--output -o`  Output file
* `--headers -H` Send custom headers
* `--data -d` HTTP POST data
* `--user-agent -A` Set User-Agent header

Here are some examples of requests.

``` shell
$ aioreq http://127.0.0.1:7575 
$ aioreq http://127.0.0.1:7575/cli_doc -d "Bob" -X POST
User Bob was created!
$ aioreq http://127.0.0.1:7575/cli_doc -o /dev/null

$ aioreq http://127.0.0.1:7575/cli_doc -v -H "custom-header: custom-value" \
                                             "second-header: second-value"
========REQUEST HEADERS========
user-agent: python/aioreq
accept: */*
custom-header: custom-value
second-header: second-value
accept-encoding:  gzip; q=1, deflate; q=1
Hello 
                               
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
The first item on this list represents the first middleware that should handle our request (i.e. the **closest middleware to our client**), while the last index represents the **closest middleware to the server**.


We can pass our modified middlewares tuple to the Client to override the default middlewares.
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

All 'aioreq' middlewares must be subclasses of the class `middlewares.MiddleWare`

MiddleWare below would add 'test-md' header if request domain is `www.example.com`
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

## SSL/TLS

Aioreq supports three attributes related to this topic.

* `check_hostname` Checks whether the peer cert hostname matches the server domain.
* `verify_mode` Specifies whether the server certificate must be verified.
* `keylog_filename` File location for dumping private keys

You can also set the environment variable `SSLKEYLOGFILE` 
instead of specifying `keylog_filename`.

You can use a tool like `wireshark` to decrypt your `HTTPS` traffic if you have a file with the private keys.

Example:

``` shell
$ export SSLKEYLOGFILE=logs
```

Then just run aioreq.

``` shell
$ aioreq https://example.com
$ ls -l
total 8
-rw-r--r-- 1 user user 406 Dec  5 17:19 logs
```
Now, the 'logs' file contains keylogs that can be used to decrypt your TLS/SSL traffic with a tool such as 'wireshark'.

Here are a few examples of how to manage the SSL context for your requests.

``` python
import aioreq
dont_verify_cert = aioreq.get("https://example.com", verify_mode=False)
verify_and_dump_logs = aioreq.get("https://example.com", verify_mode=True, keylog_filename="logs")
default_configs = aioreq.get("https://example.com", verify_mode=True, check_hostname=True)
```

## Authentication

If the `auth` parameter is included in the request, Aioreq will handle authentication.

There are two types of authorization that aioreq can handle.
* Digest Authorization
* Basic Authorization

If the incoming response status code is **401** and the header contains `www-authorization`, `aioreq` will attempt **each** of the schemes until authorization is complete.


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
Parameter `auth` should be a tuple with two elements: login and password.

Authentication is enabled by `AuthenticationMiddleWare`, so exercise caution when managing middlewares manually.

## Benchmarks

In this benchmarks, we compare `aioreq` and `httpx` during 999 asynchronous requests, without caching

You can run these tests on your **local machine**; the directory `aioreq/benchmarks\
contains all of the required modules.
```
$ cd benchmarks
$ ./run_tests
Benchmarks
---------------------------
aioreq benchmark
Total time: 2.99
---------------------------
httpx benchmark
Total time: 7.60
```


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
