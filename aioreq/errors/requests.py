from .base import AioreqError

class AsyncRequestsError(AioreqError):
    ...

class InvalidDomainName(AioreqError):
    ...

class TimeoutError(AioreqError):
    ...
