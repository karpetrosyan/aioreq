import requests

from benchmark_settings import REQUESTS_URL


def main():
    with requests.session() as s:
        for j in range(5):
            s.get(REQUESTS_URL)


if __name__ == '__main__':
    main()
