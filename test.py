# import socket
# import ssl

# hostname = 'leetcode.com'
# context = ssl.create_default_context()

# payld = ("GET / HTTP/1.1\r\n"
#          f"Host: {hostname}\r\n\r\n")
# with socket.create_connection((hostname, 443)) as sock:
#     with context.wrap_socket(sock, server_hostname=hostname) as ssock:
#         text = payld
#         ssock.sendall(text.encode())
#         print(ssock.recv(40))

import aioreq
import asyncio

cl = aioreq.Client()

resp = asyncio.run(cl.get("https://leetcode.com"))
print(resp)