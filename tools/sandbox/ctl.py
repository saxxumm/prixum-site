#!/usr/bin/env python3
"""Sends one command to the sandbox agent and prints the reply.
usage: ctl.py <cmd> [key=value ...]   numbers become numbers, a comma list of numbers becomes a list
examples: ctl.py shot path=/tmp/a.png   ctl.py click x=400 y=300 ms=400   ctl.py type text=java
"""
import json
import socket
import sys

SOCK = "/tmp/claude-1000/sandbox.sock"


def value(text):
    for kind in (lambda t: int(t, 0), float):
        try:
            return kind(text)
        except ValueError:
            pass
    if "," in text:
        try:
            return [int(v, 0) for v in text.split(",")]
        except ValueError:
            pass
    return text


def send(cmd, **args):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK)
    s.sendall((json.dumps({"cmd": cmd, **args}) + "\n").encode())
    reply = json.loads(s.makefile().readline())
    s.close()
    return reply


if __name__ == "__main__":
    args = {}
    for item in sys.argv[2:]:
        key, _, raw = item.partition("=")
        args[key] = value(raw)
    reply = send(sys.argv[1], **args)
    print(json.dumps(reply, ensure_ascii=False))
    sys.exit(0 if reply.get("ok") else 1)
