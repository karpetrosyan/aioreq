from rfcparser import core
from rfcparser.object_abstractions import Uri3986


def parse_url(url) -> Uri3986:
    return core.UriParser3986().parse(url)
