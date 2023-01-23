from .base import AioreqError


class ClosedConnectionWithoutResponse(AioreqError):
    ...


class InvalidResponseData(AioreqError):
    ...
