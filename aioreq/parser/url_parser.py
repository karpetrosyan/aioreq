import re
import logging

from dataclasses import dataclass

log = logging.getLogger('aioreq')

@dataclass
class Url:
    scheme : str
    subdomain : str
    domain : str
    top_level_domain : str
    path : str
    variables : str
    fragment : str

    def get_url(self):
        url = f"{self.scheme}://{self.subdomain}.{self.domain}.{self.top_level_domain}"
        url += self.path
        url += f'?{self.variables}' if self.variables else ''
        url += self.fragment
        return url

    def get_url_without_path(self):
        return f"{self.scheme}://{self.subdomain}.{self.domain}.{self.top_level_domain}"

    def get_url_for_dns(self):
        log.debug(f"Getting dns url for {self=}")
        return f"{self.subdomain}.{self.domain}.{self.top_level_domain}"

    def __post_init__(self):
        self.path = self.path or ''
        self.path = '/' + self.path
        self.fragment = self.fragment or ''
    
class UrlParser:
    regex = re.compile(
            r'(?P<scheme>https?)://'
            r'(?P<subdomain>www)\.'
            r'(?P<domain>.*?)\.'
            r'(?P<top_level_domain>.*?)/'
            r'(?:(?P<path>.*)((?:\?'
            r'(?P<variables>.*))'
            r'(?:#(?P<fragment>.*))?)?)?')

    
    @classmethod
    def parse(cls, url) -> Url:
        matched = cls.regex.search(url)

        if not matched:
            raise ValueError(f"Invalid url {url}")

        scheme = matched.group('scheme')
        subdomain = matched.group('subdomain')
        domain = matched.group('domain')
        top_level_domain = matched.group('top_level_domain')
        path = matched.group('path')
        variables = matched.group('variables')
        fragment = matched.group('fragment')
        return Url(
                scheme,
                subdomain,
                domain,
                top_level_domain,
                path,
                variables,
                fragment
                )

