## Headers

To work with headers, 'Aioreq' provides special 'BaseHeader' subclasses.

We can set the Accept header by simply entering it in the 'Headers' field, as shown here.
``` py
>>> import aioreq
>>> headers = aioreq.Headers({'Accept' : 'application/json'})
```

We can also prioritize values.
``` py
>>> headers = aioreq.Headers({"Accept" : "application/json; q=1"})
```

If you want, you can use the dictionary interface.
``` py
>>> headers = aioreq.Headers()
>>> headers['accept'] = 'application/json; q=1'
```


However, aioreq's special 'BaseHeader' subclasses can also be used.

Why should you use header classes?
You can use the editor autocomplete to add headers without knowing anything about header syntax.

``` py
>>> from aioreq import headers
>>> headers = aioreq.Headers()
>>> headers.add_header(headers.Accept(
>>>    (headers.MimeType.json, 1),
>>> ))
>>> headers
Headers:
    accept : application/json; q=1
```

First, we should import headers.
``` py
>>> from aioreq import headers
```

Then, make a `BaseHeader` object.
``` py
>>> header_obj = headers.Accept(
>>>     (headers.MimeType.html, 0.5)
>>> ) 
```

This is the 'Accept' header object, with the value 'application/html; q=0.5,' 
where 'q' is the priority for that 'MimeType.'
Finally, insert this header into the 'Headers' object.
``` py
>>> headers.add_header(header_obj)
>>> headers
Headers:
    accept : application/html; q=0.5
```

We can also add multiple 'Values' in this manner.
``` py
>>> header_obj = Accept(
>>>     (headers.MimeType.html, 0.6),
>>>     (headers.MimeType.json, 0.8)
>>> )
>>> headers.add_header(header_obj)
>>> headers:
Headers:
    accept: application/html; q=0.6, application/json; q=0.8 
```

That is, the client accepts both html and json responses, but please provide me with a json response if you support both.

## Client

The `Client` class offers a high-level API for sending and receiving HTTP/1.1 requests.
That is how the 'Client' class works.

``` py
>>> import aioreq
>>> async def main():
>>>     async with aioreq.Client() as client:
>>>         ...
```

To change some default arguments or enable persistent connections, pass arguments through the 'Client.'

``` py
>>> async def main():
>>>     async with aioreq.Client(headers = {'test' : 'test1'}) as client:
>>>         await client.get('http://example.com') # This request includes the 'test' header, which was added by the client.
>>>         await client.get('http://example.com', headers = {'test' : 'test2'}) # Overrides the client headers.
```

You can also use HTTP/1.1's main feature, persistent connections, to save a significant amount of memory and system 
resources by reusing connections rather than creating new ones.

``` py
>>> async def main():
>>>     async with aioreq.Client(persistent_connections = True) as client:
>>>         ... # This client can now reuse previously opened connections.
```

In order to improve request performance, 'Aioreq' instructs the server to encode HTTP messages if possible.

This feature is very useful, but you can disable it for specific 'Client' objects if you want.

``` py
>>> client = aioreq.Client(enable_encodings=False)
```





