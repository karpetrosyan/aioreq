import logging
import re
from dataclasses import dataclass
from typing import Union

from ..errors.parser import UrlParsingError

log = logging.getLogger('aioreq')


@dataclass
class Url:
    """
    Url class which stores url information

    This class used to store url information as attributes
    and gives interface to get specific part of that url

    :param protocol: Url protocol
    :type protocol: str or None
    :param subdomain: URL subdomain
    :type subdomain: str or None
    :param domain: URL domain
    :type domain: str or None
    :param top_level_domain: Top level domain like 'com' or 'ru' or 'am'
    :type top_level_domain: str or None
    :param path: Url path which comes after top level domain, like /users/id/132
    :type path: str or None
    :param variables: Variables which comes after path, like '?name=kar1&profession=programmer&group=&'
    :type variables: str or None
    :param fragment: Url fragment comes after varaibles like  #test where test is the fragment
    :type fragment: str or None
    """

    protocol: Union[str, None]
    subdomain: Union[str, None]
    domain: str
    top_level_domain: str
    path: str
    variables: Union[str, None]
    fragment: Union[str, None]

    def get_url(self):
        """
        Getting the full url

        :returns: full url
        :rtype: str
        """

        if self.subdomain:
            url = f"{self.protocol}://{self.subdomain}.{self.domain}.{self.top_level_domain}"
        else:
            url = f"{self.protocol}://{self.domain}.{self.top_level_domain}"
        url += self.path
        url += f'?{self.variables}' if self.variables else ''
        url += self.fragment or ''
        return url

    def get_url_without_path(self):
        """
        Getting pathless url

        :returns: pathless url
        :rtype: str
        """

        if self.subdomain:
            return f"{self.protocol}://{self.subdomain}.{self.domain}.{self.top_level_domain}"
        return f"{self.protocol}://{self.domain}.{self.top_level_domain}"

    def get_url_for_dns(self):
        """
        Getting only domains from the url

        :returns: joined domains with '.' char
        :rtype: str
        """

        if self.subdomain:
            return f"{self.subdomain}.{self.domain}.{self.top_level_domain}"
        return f"{self.domain}.{self.top_level_domain}"

    def __post_init__(self):
        """
        Function which dataclasses calls after __init__ done
        """

        self.path = self.path or '/'


class UrlParser:
    """
    Url parser which parse url and gives Url object
    """

    # regex which getting parts from the url
    regex = re.compile(
        r'(?P<protocol>https?)://'
        r'((?P<subdomain>[^\.]+)\.)?'
        r'(?P<domain>[^\.]+)\.'
        r'(?P<top_level_domain>[^/#]+)'
        r'(?P<port>\d+)?'
        r'(?:(?P<path>/[^#?]*)((?:\?'
        r'(?P<variables>[^#]*)?))?)?'
        r'(?:#(?P<fragment>.*))?'
    )

    @classmethod
    def parse(cls, url: str) -> Url:
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
            raise UrlParsingError(url)

        protocol = matched.group('protocol')
        subdomain = matched.group('subdomain')
        domain = matched.group('domain')
        top_level_domain = matched.group('top_level_domain')
        path = matched.group('path')
        variables = matched.group('variables')
        fragment = matched.group('fragment')
        return Url(
            protocol,
            subdomain,
            domain,
            top_level_domain,
            path,
            variables,
            fragment
        )
