import hashlib
import os
import time
from base64 import b64encode
from enum import Enum

from .headers import AuthenticationWWW

HASH_FUNCTIONS_MAP = {
    "MD5": hashlib.md5,
    "SHA": hashlib.sha1,
    "SHA-256": hashlib.sha256,
    "SHA-512": hashlib.sha512,
    "MD5-SESS": hashlib.md5,
    "SHA-SESS": hashlib.sha1,
    "SHA-256-SESS": hashlib.sha256,
    "SHA-512-SESS": hashlib.sha512,
}


def get_client_nonce(nonce_count, nonce):
    s = str(nonce_count).encode() + nonce
    s += time.ctime().encode()
    s += os.urandom(8)
    return hashlib.sha1(s).hexdigest()[:16].encode()


def unq(text):
    return text.strip(b'"')


def authenticate_basic(params, request, response) -> str:
    return (
        "Basic " + b64encode(f"{request.auth[0]}:{request.auth[1]}".encode()).decode()
    )


def authenticate_digest(params, request, response) -> str:
    realm = unq(params.get("realm", "").encode())
    nonce = unq(params.get("nonce", "").encode())
    opaque = unq(params.get("opaque", "").encode())
    algorithm = params.get("algorithm", "MD5")
    qop = unq(params.get("qop", "").encode())
    nc = 1
    nc_value = b"%08x" % nc
    cnonce = get_client_nonce(nc, nonce)

    username, password = request.auth
    algorithm_function = HASH_FUNCTIONS_MAP[algorithm.upper()]
    username = username.encode()
    password = password.encode()

    if qop and qop != b"auth":
        raise ValueError("Aioreq does not support `auth-int` qop yet.")

    def digest(data):
        return algorithm_function(data).hexdigest().encode()

    A1 = b":".join((username, realm, password))

    path = request.url.path_and_query().encode()

    if algorithm.lower().endswith("-sess"):
        A1 = (digest(A1), nonce, cnonce)
    A2 = b":".join((request.method.encode(), path))

    if qop:
        response = digest(
            b":".join((digest(A1), nonce, nc_value, cnonce, qop, digest(A2)))
        )
    else:
        response = digest(b":".join((digest(A1), nonce, digest(A2))))
    response = response.decode()
    qop = qop.decode()
    nonce = nonce.decode()
    cnonce = cnonce.decode()
    realm = realm.decode()
    username = username.decode()
    nc_value = nc_value.decode()
    opaque = opaque.decode()
    path = path.decode()
    authorization_string = (
        f'Digest username="{username}", realm="{realm}", nonce="{nonce}", '
        f'uri="{path}"'
    )
    if qop:
        authorization_string += f', qop={qop}, nc={nc_value}, cnonce="{cnonce}", '
    authorization_string += f', response="{response}"'
    if opaque:
        authorization_string += f', opaque="{opaque}"'
    return authorization_string


class AuthenticationSchemes(Enum):
    BASIC = "Basic"
    DIGEST = "Digest"

    def authenticate(self, *args, **kwargs):
        if self == AuthenticationSchemes.BASIC:
            return authenticate_basic(*args, **kwargs)
        elif self == AuthenticationSchemes.DIGEST:
            return authenticate_digest(*args, **kwargs)


def parse_auth_header(header: AuthenticationWWW, request, response):
    authentication_schemes = [
        AuthenticationSchemes(scheme) for scheme in header.auth_schemes
    ]

    for authentication_scheme in authentication_schemes:
        try:
            authorization_string = authentication_scheme.authenticate(
                header.auth_schemes[authentication_scheme.value], request, response
            )
            yield authorization_string
        except ValueError:
            ...
