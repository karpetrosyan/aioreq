# CHANGELOG

## 1.0.4

### Removed

* Lark has been removed from the dependencies.
* Rfcparser has been removed from the dependencies.
* Fastapi has been removed from the optional dependencies.

### Update

* Rfcparser has been merged with the aioreq.
* Replace fastapi with starlette. 

### Added

* Python3.8 and Python3.9 testing with tox.
* Synchronous interface for aioreq.
* Starlette has been added as an optional dependency.

## 1.0.2

### Added

* Cookies
* RFC 3896 uri syntax is now completely supported. (i.e http://127.0.0.1:5050 or http://test.com:20 now are valid)
* Multivalue headers support (e.g Set-Cookie, WWW-Authenticate)

### Updated

* HTTP response parsing algorithm
* Stream responses interface
* utils.wrap_errors now is a context manager
* The certifi library has been removed from the dependencies.
* Rfcparser is a new dependency that handles parsing strongly with rfc grammars.

### Fixed

* SSL handshake failure with some servers
* JSON encoding issues

## 1.0.1

### Added

* Middlewares support
* Basic authentication
* [Lark](https://github.com/lark-parser/lark) has been added as a new dependency
* Support for earlier versions of Python (3.7>=)

### Fixed

* Deflate encoding
* Fix middleware doctests
* Fix server process killing for windows
* Fix middleware doctests


### Removed

* Clients 'enable_encodings' parameter
* The legacy 'timeout' has been replaced by the new 'TimeoutMiddleWare'
* pytest.ini file
