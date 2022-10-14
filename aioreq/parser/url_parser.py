import re
import logging

from dataclasses import dataclass

log = logging.getLogger('aioreq')

@dataclass
class Url:
    """
    Url class which stores url information

    This class used to store url information as attributes
    and gives interface to get specific part of that url

    :param scheme: HTTP protocol scheme for example HTTP or 'rtsp' which is'n supported in this library
    :param subdomain: URL subdomain like 'www'
    :param domain: URL domain like youtube
    :param top_level_domain: Top level domain like 'com' or 'ru' or 'am'
    :param path: Url path which comes after top level domain, like /users/id/132
    :param variables: Variables which comes after path, like '?name=kar1&profession=programmer&group=&'
    :param fragment: Url fragment comes after varaibles like  #test where test is the fragment
    """

    scheme : str
    subdomain : str
    domain : str
    top_level_domain : str
    path : str
    variables : str
    fragment : str

    def get_url(self):
        """
        Getting the full url

        :returns: full url
        :rtype: str
        """

        url = f"{self.scheme}://{self.subdomain}.{self.domain}.{self.top_level_domain}"
        url += self.path
        url += f'?{self.variables}' if self.variables else ''
        url += self.fragment
        return url

    def get_url_without_path(self):
        """
        Getting pathless url

        :returns: pathless url
        :rtype: str
        """

        return f"{self.scheme}://{self.subdomain}.{self.domain}.{self.top_level_domain}"

    def get_url_for_dns(self):
        """
        Getting only domains from the url

        :returns: joined domains with '.' char
        :rtype: str
        """

        return f"{self.subdomain}.{self.domain}.{self.top_level_domain}"

    def __post_init__(self):
        """
        Function which dataclasses calls after __init__ done
        """

        self.path = self.path or ''
        self.path = '/' + self.path
        self.fragment = self.fragment or ''
    
class UrlParser:
    """
    Url parser which parse url and gives Url object
    """
    
    # regex which getting parts from the url
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
        """
        The main function for this class, which parse url string

        Parsing raw url using regular expressions, creating Url object
        and returning

        :param url: url string
        :returns: Url object with attributes like url parts
        :rtype: Url
        """

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

