#!/usr/bin/env python3
"""Outside half of the sandbox proxy: HTTP proxy on a unix socket that connects to the internet.
Login servers are refused so the demo account never sends its fake tokens anywhere."""
import os, socket, sys, threading

SOCK = sys.argv[1]
BLOCKED = ("login.microsoftonline.com", "login.live.com", "xboxlive.com", "api.minecraftservices.com", "authserver.ely.by", "account.ely.by")

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
    head = b""
    while b"\r\n\r\n" not in head:
        chunk = client.recv(4096)
        if not chunk:
            client.close(); return
        head += chunk
    line = head.split(b"\r\n", 1)[0].decode("latin1")
    method, target, _ = line.split(" ", 2)
    if method == "CONNECT":
        host, port = target.rsplit(":", 1)
        rest = b""
    else:
        # absolute-form request for plain http
        after = target.split("://", 1)[1]
        hostport = after.split("/", 1)[0]
        host, port = (hostport.rsplit(":", 1) + ["80"])[:2] if ":" in hostport else (hostport, "80")
        rest = head
    if any(host == b or host.endswith("." + b) for b in BLOCKED):
        client.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n"); client.close()
        print("blocked", host, flush=True); return
    try:
        upstream = socket.create_connection((host, int(port)), timeout=20)
        upstream.settimeout(None)
    except OSError as e:
        client.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n"); client.close(); return
    if method == "CONNECT":
        client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        extra = head.split(b"\r\n\r\n", 1)[1]
        if extra:
            upstream.sendall(extra)
    else:
        upstream.sendall(rest)
    threading.Thread(target=relay, args=(client, upstream), daemon=True).start()
    relay(upstream, client)

if os.path.exists(SOCK):
    os.unlink(SOCK)
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(SOCK)
os.chmod(SOCK, 0o600)
server.listen(64)
while True:
    conn, _ = server.accept()
    threading.Thread(target=handle, args=(conn,), daemon=True).start()
