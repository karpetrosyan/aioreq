import re

from .base import AioreqError


class UrlParsingError(AioreqError):
    def __init__(self, *args):
        text = "Can't handle this URL parsing error, please report your problem and help this project to be better"

        for i in range(1):
            (url,) = args
            if not (url.startswith("http") or url.startswith("https")):
                text = "Url should starts with `http://` or `https://`."
                break
            else:
                scheme_len = 7 if url.startswith("http://") else 8
                splited = url[scheme_len:]

                match = re.match(
                    r"(.+?\.)?(?P<domain>.*?)\.(?P<top_domain>.*)[/$]", splited
                )

                if match:
                    domain, top_level_domain = bool(match.group("domain")), bool(
                        match.group("top_domain")
                    )
                    two_parts = (not domain) and (not top_level_domain)

                    missing_parts = (
                        ("Domain" if not domain else "Top-level-domain")
                        if not two_parts
                        else ("Domain", "Top-level-domain")
                    )

                    text = (
                        f"Missing url part{'s' if two_parts else ''}: {missing_parts}"
                    )

                    break
                else:
                    text = "Unexpected domain syntax."
                    break

        super(UrlParsingError, self).__init__(text)
