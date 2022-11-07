import requests

with requests.session() as s:
    for j in range(100):
        s.get('https://www.google.com')
