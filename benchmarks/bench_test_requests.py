import requests

from benchmark_settings import REQUESTS_URL
from benchmark_settings import SYNC_REQUESTS_COUNT


def main():
    with requests.session() as s:
        codes = []
        for j in range(SYNC_REQUESTS_COUNT):
            resp = s.get(REQUESTS_URL)
            codes.append(resp.status_code)
        return codes


if __name__ == '__main__':
    main()
