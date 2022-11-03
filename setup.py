from setuptools import setup
from setuptools import find_packages

setup(
        name="aioreq",
        version='0.0.3',
        description="Async requests lib",
        install_requires = [
            'certifi'
            ],
        extras_require={
            'tests' : [
                'pytest',
                'pytest-asyncio'
                ]
            },
        packages = find_packages(),
        include_package_data=True,
        package_data={'aioreq':['*.ini']}
        )
