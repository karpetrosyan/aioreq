import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Union, Tuple
from ..errors.base import UnexpectedError
from . import codes
from .auth import parse_auth_header
from .encodings import get_avaliable_encodings
from .headers import AuthenticationWWW, SetCookie
from .headers import ContentEncoding
from .headers import TransferEncoding
from ..errors.requests import RequestTimeoutError
from ..settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)

default_middlewares = (
    "RetryMiddleWare",
    "RedirectMiddleWare",
    "CookiesMiddleWare",
    "DecodeMiddleWare",
    "AuthenticationMiddleWare",
)


def load_class(name):
    if "." not in name:
        return globals()[name]
    components = name.split(".")
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


class MiddleWare(ABC):
    def __init__(self, next_middleware):
        self.next_middleware = next_middleware

    @abstractmethod
    async def process(self, request, client):
        ...

    @staticmethod
    def build(
        middlewares_: Union[
            Tuple[Union[str, type], ...],
        ]
    ):
        result = TimeoutMiddleWare(RequestMiddleWare(next_middleware=None))
        for middleware in reversed(middlewares_):
            if isinstance(middleware, str):
                result = load_class(middleware)(next_middleware=result)
            else:
                result = middleware(next_middleware=result)
        return result


class RequestMiddleWare(MiddleWare):
    async def process(self, request, client):
        resp = await client.send_request_directly(request)
        return resp


class RedirectMiddleWare(MiddleWare):
    redirect_count = 3

    def __init__(self, *args, **kwargs):
        redirect = kwargs.get("redirect", None)
        if not redirect:
            redirect = self.redirect_count
        self.redirect = max(redirect + 1, 1)
        self.memory = {}
        super().__init__(*args, **kwargs)

    def contains_location(self, response):
        return "location" in response.headers

    async def handle_301(self, request, response):
        if not self.contains_location(response):
            return False
        new_location = response.headers["location"]
        old_url = request.url

        if new_location.startswith("http"):
            request.url = new_location
            self.memory[str(old_url)] = new_location
        else:
            request.path = new_location
            self.memory[str(old_url)] = request.host + new_location
        return True

    async def handle_302(self, request, response):
        if not self.contains_location(response):
            return False
        new_location = response.headers["location"]
        log.critical(new_location)
        if new_location.startswith("http"):
            request.url = new_location
        else:
            request.path = new_location
        return True

    async def handle_303(self, request, response):
        if not self.contains_location(response):
            return False
        new_location = response.headers["location"]
        request.method = "GET"
        request.context = b""
        if new_location.startswith("http"):
            request.url = new_location
        return True

    async def handle_304(self, request, response):
        assert True, "304 status code received by the server"

    async def handle_305(self, *args, **kwargs):
        return False

    async def handle_306(self, request, response):
        return False

    async def handle_307(self, request, response):
        return await self.handle_302(request, response)

    async def handle_308(self, request, response):
        return await self.handle_301(request, response)

    async def process(self, request, client):
        redirect = self.redirect
        response = None
        while redirect != 0:
            redirect -= 1

            response = await self.next_middleware.process(request, client)
            if (response.status // 100) == 3:
                handler = getattr(self, f"handle_{response.status}", None)

                if handler is None:
                    raise ValueError(
                        f"Handler for {response.status} status code was not implemented"
                    )
                continue_ = await handler(request, response)

                if redirect < 1 or not continue_:
                    return response
            else:
                return response
        assert response is not None

        return response


class DecodeMiddleWare(MiddleWare):
    def decode(self, response):
        for parser, header in (
            (TransferEncoding, "transfer-encoding"),
            (ContentEncoding, "content-encoding"),
        ):
            header_content = response.headers.get(header, None)
            if header_content:
                encodings = parser.parse(header_content)

                for encoding in encodings:
                    response.content = encoding.decompress(response.content)

    async def process(self, request, client):

        request.headers.add_header(get_avaliable_encodings())

        response = await self.next_middleware.process(request, client)
        self.decode(response)
        return response


class RetryMiddleWare(MiddleWare):
    retry_count = 3

    def __init__(self, *args, **kwargs):
        self.retry_count = max(self.retry_count + 1, 1)
        super().__init__(*args, **kwargs)

    async def process(self, request, client):
        retry_count = self.retry_count
        response = None
        while retry_count != -1:
            retry_count -= 1
            try:
                response = await self.next_middleware.process(request, client)
                break
            except Exception as e:
                if isinstance(e, UnexpectedError):
                    raise e
                if retry_count == -1:
                    raise e
        return response


class AuthenticationMiddleWare(MiddleWare):
    async def process(self, request, client):

        resp = await self.next_middleware.process(request, client)
        if request.auth:
            if resp.status != codes.UNAUTHORIZED:
                return resp
            if "www-authenticate" not in resp.headers:
                raise ValueError(
                    f"{codes.UNAUTHORIZED} status code received without `www-authenticate` header"
                )
            header_obj = AuthenticationWWW.parse(resp.headers["www-authenticate"])
            for authentication_header in parse_auth_header(header_obj, request):
                request.headers["authorization"] = authentication_header
                resp = await self.next_middleware.process(request, client)
                if resp.status != codes.UNAUTHORIZED:
                    break
        return resp


class TimeoutMiddleWare(MiddleWare):
    async def process(self, request, client):

        try:
            return await asyncio.wait_for(
                self.next_middleware.process(request, client),
                timeout=request.timeout or client.timeout,
            )
        except asyncio.TimeoutError:
            raise RequestTimeoutError from None


class CookiesMiddleWare(MiddleWare):
    async def process(self, request, client):
        cookies = client.cookies.get_raw_cookies()
        request.headers["cookie"] = cookies
        resp = await self.next_middleware.process(request, client)

        if "set-cookie" in resp.headers:
            set_cookies = [
                SetCookie.parse(cookie_value)
                for cookie_value in resp.headers["set-cookie"]
            ]
            for set_cookie in set_cookies:
                client.cookies.add_cookie(set_cookie)
        return resp
