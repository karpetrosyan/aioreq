# CHANGELOG

## 1.0.1

### Added

* Middlewares support.
* Basic authentication.
* [Lark](https://github.com/lark-parser/lark) has been added as a new dependency.
* Support for earlier versions of Python (3.7>=)

### Fixed

* Deflate encoding.
* Fix middleware doctests
* Fix server process killing for windows
* Fix middleware doctests


### Removed

* Clients 'enable_encodings' parameter.
* The legacy 'timeout' has been replaced by the new 'TimeoutMiddleWare'.
* pytest.ini file
