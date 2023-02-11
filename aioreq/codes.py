# Informational

CONTINUE = 100
SWITCHING_PROTOCOLS = 101

# 2xx Ok

OK = 200
CREATED = 201
ACCEPTED = 202
NON_AUTHORITATIVE_INFORMATION = 203
NO_CONTENT = 204
RESET_CONTENT = 205
PARTIAL_CONTENT = 206

# 3xx Redirects

MULTIPLE_CHOICES = 300
MOVED_PERMANENTLY = 301
FOUND = 302
SEE_OTHER = 303
NOT_MODIFIED = 304
USE_PROXY = 305
TEMPORARY_REDIRECT = 307

# 4xx Client errors

BAD_REQUEST = 400
UNAUTHORIZED = 401
PAYMENT_REQUIRED = 402
FORBIDDEN = 403
NOT_FOUND = 404
METHOD_NOT_ALLOWED = 405
NOT_ACCEPTABLE = 406
PROXY_AUTHENTICATION_REQUIRED = 407
REQUEST_TIMEOUT = 408
CONFLICT = 409


def is_informational(code: int) -> bool:
    return code // 100 == 1


def is_ok(code: int) -> bool:
    return code // 100 == 2


def is_redirect(code: int) -> bool:
    return code // 100 == 3


def is_client_error(code: int) -> bool:
    return code // 100 == 4


def is_server_error(code: int) -> bool:
    return code // 100 == 5
