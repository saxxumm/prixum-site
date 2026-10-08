#!/usr/bin/env python3
"""Inside half: TCP 127.0.0.1:3128 in the sandbox, forwarded to the unix socket of proxy_out.py."""
import socket, sys, threading

SOCK = sys.argv[1]

def relay(a, b):
    try:
        while True:
            data = a.recv(65536)
            if not data:
                break
            b.sendall(data)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

def handle(client):
    upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    upstream.connect(SOCK)
    threading.Thread(target=relay, args=(client, upstream), daemon=True).start()
    relay(upstream, client)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("127.0.0.1", 3128))
server.listen(64)
while True:
    conn, _ = server.accept()
    threading.Thread(target=handle, args=(conn,), daemon=True).start()
