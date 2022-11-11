from setuptools import setup
from setuptools import find_packages

long_description = open('README.md').read()

setup(
    name="aioreq",
    version='0.0.5',
    description="Async requests lib",
    install_requires=[
        'certifi',
        'dnspython'
    ],
    extras_require={
        'tests': [
            'pytest',
            'pytest-asyncio',
            'uvicorn',
            'fastapi',
        ],
        'benchmark': [
            'aiohttp',
            'httpx',
            'requests',
        ],
        'uvloop': [
            'uvloop'
        ]
    },
    packages=find_packages(),
    include_package_data=True,
    package_data={'aioreq': ['*.ini']},
    long_description=long_description,
    long_description_content_type='text/markdown'
)
