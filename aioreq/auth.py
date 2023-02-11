from .headers import AuthenticationWWW
from base64 import b64encode
from enum import Enum


def authenticate_basic(params, request) -> str:
    return (
        "Basic " + b64encode(f"{request.auth[0]}:{request.auth[1]}".encode()).decode()
    )


def authenticate_digest(params, request) -> str:
    raise NotImplementedError()


class AuthenticationSchemes(Enum):
    BASIC = "Basic"
    DIGEST = "Digest"

    def authenticate(self, *args, **kwargs):

        if self == AuthenticationSchemes.BASIC:
            return authenticate_basic(*args)
        elif self == AuthenticationSchemes.DIGEST:
            return authenticate_digest(**kwargs)


def parse_auth_header(header: AuthenticationWWW, request):
    authentication_schemes = [
        AuthenticationSchemes(scheme) for scheme in header.auth_schemes
    ]

    for authentication_scheme in authentication_schemes:
        yield authentication_scheme.authenticate(
            header.auth_schemes[authentication_scheme.value], request
        )
