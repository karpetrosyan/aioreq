from .base import AioreqError


class AsyncRequestsError(AioreqError):
    ...


class InvalidDomainName(AioreqError):
    ...


class RequestTimeoutError(AioreqError):
    ...


class ConnectionTimeoutError(AioreqError):
    ...
