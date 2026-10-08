#!/usr/bin/env python3
"""Runs a launcher on a private Qt VNC screen and takes commands on a unix socket: screenshots, mouse and keyboard
input, and screen recordings. The VNC screen has no cursor, recordings get a drawn one and a ripple on every click.

usage: agent.py <control socket> <log file> <launcher> [args...]
env:   VW, VH screen size in pixels (QT_SCALE_FACTOR sets how large the interface is drawn on it)

Commands are one JSON object per connection, see handle() for the list. Meant to run inside a network namespace
with only loopback, so the VNC port is unreachable from outside.
"""
import json
import math
import os
import socket
import struct
import subprocess
import sys
import threading
import time

from PIL import Image, ImageDraw

sock_path, log_path, *launcher = sys.argv[1:]
W, H = int(os.environ.get("VW", 1920)), int(os.environ.get("VH", 1200))
SCALE = float(os.environ.get("QT_SCALE_FACTOR", "1"))
PORT = 5912

env = dict(os.environ)
env["QT_QPA_PLATFORM"] = f"vnc:size={W}x{H}:port={PORT}"
env.pop("WAYLAND_DISPLAY", None)
env.pop("DISPLAY", None)
proc = subprocess.Popen(launcher, env=env, stdout=open(log_path, "w"), stderr=subprocess.STDOUT)


def recv_exact(s, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("the vnc server closed the connection")
        buf += chunk
    return bytes(buf)


class Screen:
    """An RFB client whose reader thread keeps the framebuffer current with incremental updates."""

    def __init__(self):
        for _ in range(150):
            try:
                self.s = socket.create_connection(("127.0.0.1", PORT))
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("the vnc server did not start")
        version = recv_exact(self.s, 12)
        if version.startswith(b"RFB 003.008"):
            self.s.sendall(b"RFB 003.008\n")
            count = recv_exact(self.s, 1)[0]
            types = recv_exact(self.s, count)
            assert 1 in types, types
            self.s.sendall(b"\x01")
            assert struct.unpack(">I", recv_exact(self.s, 4))[0] == 0
        else:
            self.s.sendall(b"RFB 003.003\n")
            assert struct.unpack(">I", recv_exact(self.s, 4))[0] == 1
        self.s.sendall(b"\x01")  # shared
        self.w, self.h = struct.unpack(">HH", recv_exact(self.s, 4))
        recv_exact(self.s, 16)
        recv_exact(self.s, struct.unpack(">I", recv_exact(self.s, 4))[0])
        # 32 bit little endian 0x00RRGGBB, so the bytes are B G R X
        pf = struct.pack(">BBBBHHHBBBxxx", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
        self.s.sendall(b"\x00\x00\x00\x00" + pf)
        self.s.sendall(struct.pack(">BxHi", 2, 1, 0))  # raw encoding only
        self.fb = bytearray(self.w * self.h * 4)
        self.lock = threading.Lock()
        self.send_lock = threading.Lock()
        self.updated = threading.Condition(self.lock)
        self.version = 0
        self.pointer = (self.w // 2, self.h // 2)
        self.buttons = 0
        self.clicks = []
        threading.Thread(target=self._reader, daemon=True).start()

    def send(self, data):
        with self.send_lock:
            self.s.sendall(data)

    def _reader(self):
        incremental = 0
        stride = self.w * 4
        while True:
            self.send(struct.pack(">BBHHHH", 3, incremental, 0, 0, self.w, self.h))
            incremental = 1
            kind = recv_exact(self.s, 1)[0]
            if kind == 0:
                recv_exact(self.s, 1)
                rects = struct.unpack(">H", recv_exact(self.s, 2))[0]
                for _ in range(rects):
                    x, y, w, h, enc = struct.unpack(">HHHHi", recv_exact(self.s, 12))
                    if enc != 0:
                        raise RuntimeError(f"unexpected encoding {enc}")
                    data = recv_exact(self.s, w * h * 4)
                    with self.lock:
                        for row in range(h):
                            start = (y + row) * stride + x * 4
                            self.fb[start:start + w * 4] = data[row * w * 4:(row + 1) * w * 4]
                with self.lock:
                    self.version += 1
                    self.updated.notify_all()
            elif kind == 2:  # bell
                pass
            elif kind == 3:  # server cut text
                recv_exact(self.s, 3)
                recv_exact(self.s, struct.unpack(">I", recv_exact(self.s, 4))[0])
            else:
                raise RuntimeError(f"unexpected server message {kind}")

    def frame(self):
        with self.lock:
            data = bytes(self.fb)
        return Image.frombuffer("RGB", (self.w, self.h), data, "raw", "BGRX", 0, 1)

    def settle(self, quiet=0.35, limit=6.0):
        """waits until the screen stopped changing for a moment"""
        end = time.time() + limit
        while time.time() < end:
            with self.lock:
                before = self.version
                self.updated.wait(quiet)
                if self.version == before:
                    return

    # ---------- input ----------
    def move(self, x, y):
        self.pointer = (int(x), int(y))
        self.send(struct.pack(">BBHH", 5, self.buttons, *self.pointer))

    def glide(self, x, y, ms):
        """moves the pointer along an eased path, the way a hand would"""
        x0, y0 = self.pointer
        steps = max(1, int(ms / 1000 * 60))
        for i in range(1, steps + 1):
            t = i / steps
            e = t * t * (3 - 2 * t)
            self.move(x0 + (x - x0) * e, y0 + (y - y0) * e)
            time.sleep(1 / 60)

    def press(self, button=1):
        self.buttons |= button
        self.send(struct.pack(">BBHH", 5, self.buttons, *self.pointer))
        if button == 1:
            self.clicks.append((*self.pointer, time.time()))

    def release(self, button=1):
        self.buttons &= ~button
        self.send(struct.pack(">BBHH", 5, self.buttons, *self.pointer))

    def click(self, button=1, count=1):
        for _ in range(count):
            self.press(button)
            time.sleep(0.07)
            self.release(button)
            time.sleep(0.09)

    def key(self, keysym):
        self.send(struct.pack(">BBxxI", 4, 1, keysym))
        time.sleep(0.03)
        self.send(struct.pack(">BBxxI", 4, 0, keysym))

    def chord(self, keysyms):
        for k in keysyms:
            self.send(struct.pack(">BBxxI", 4, 1, k))
            time.sleep(0.03)
        for k in reversed(keysyms):
            self.send(struct.pack(">BBxxI", 4, 0, k))
            time.sleep(0.03)


def make_cursor(scale):
    """the usual arrow, white with a dark outline, its tip at (pad, pad)"""
    s = scale * 1.15
    pts = [(0, 0), (0, 17), (4, 13), (7, 20), (10, 19), (7, 12.5), (12.5, 12.5)]
    pad = 3
    size = (int(16 * s) + pad * 2, int(23 * s) + pad * 2)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    poly = [(pad + x * s, pad + y * s) for x, y in pts]
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon([(x + s, y + 1.5 * s) for x, y in poly], fill=(0, 0, 0, 70))
    img.alpha_composite(shadow)
    d.polygon(poly, fill=(255, 255, 255, 255), outline=(20, 16, 24, 255), width=max(1, int(round(1.3 * s))))
    return img, pad


class Recorder:
    """writes frames at a fixed rate to ffmpeg, the last framebuffer state plus the cursor and click ripples"""

    def __init__(self, screen, path, fps, width):
        self.screen = screen
        self.fps = fps
        self.cursor, self.pad = make_cursor(SCALE)
        # a fast, nearly lossless capture; the files for the web are encoded from it afterwards
        vf = f"scale={width}:-2:flags=lanczos" if width and width != screen.w else "null"
        self.ff = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{screen.w}x{screen.h}",
             "-r", str(fps), "-i", "-", "-vf", vf, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "8",
             "-pix_fmt", "yuv444p", path],
            stdin=subprocess.PIPE)
        self.running = True
        self.frames = 0
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _overlay(self, img, now):
        draw = ImageDraw.Draw(img, "RGBA")
        for x, y, t in list(self.screen.clicks):
            p = (now - t) / 0.45
            if 0 <= p <= 1:
                r = (10 + 26 * p) * SCALE
                a = int(200 * (1 - p))
                draw.ellipse((x - r, y - r, x + r, y + r), outline=(255, 95, 162, a), width=max(2, int(3 * SCALE)))
        x, y = self.screen.pointer
        img.paste(self.cursor, (x - self.pad, y - self.pad), self.cursor)

    def _run(self):
        start = time.time()
        while self.running:
            delay = start + self.frames / self.fps - time.time()
            if delay > 0:
                time.sleep(delay)
            img = self.screen.frame()
            self._overlay(img, time.time())
            data = img.tobytes()
            # frames follow the clock: when the capture falls behind, a frame repeats instead of time shrinking
            due = max(self.frames + 1, int((time.time() - start) * self.fps))
            while self.frames < due:
                self.ff.stdin.write(data)
                self.frames += 1

    def stop(self):
        self.running = False
        self.thread.join()
        self.ff.stdin.close()
        self.ff.wait()
        return self.frames


screen = Screen()
recorder = None
screen.settle(quiet=1.0, limit=30)


def handle(req):
    global recorder
    cmd = req["cmd"]
    if cmd == "info":
        return {"w": screen.w, "h": screen.h, "scale": SCALE, "running": proc.poll() is None}
    if cmd == "shot":
        if req.get("settle", True):
            screen.settle()
        img = screen.frame()
        if req.get("crop"):
            img = img.crop(tuple(req["crop"]))
        img.save(req["path"])
        return {"size": img.size}
    if cmd == "settle":
        screen.settle(req.get("quiet", 0.35), req.get("limit", 6))
        return {}
    if cmd == "move":
        screen.move(req["x"], req["y"])
        return {}
    if cmd == "glide":
        screen.glide(req["x"], req["y"], req.get("ms", 500))
        return {}
    if cmd == "click":
        if "x" in req:
            if req.get("ms"):
                screen.glide(req["x"], req["y"], req["ms"])
            else:
                screen.move(req["x"], req["y"])
            time.sleep(0.05)
        screen.click(req.get("button", 1), req.get("count", 1))
        return {}
    if cmd == "drag":
        screen.glide(req["x0"], req["y0"], req.get("approach", 300))
        screen.press()
        time.sleep(0.08)
        screen.glide(req["x1"], req["y1"], req.get("ms", 500))
        time.sleep(0.08)
        screen.release()
        return {}
    if cmd == "key":
        screen.key(int(str(req["keysym"]), 0))
        return {}
    if cmd == "chord":
        screen.chord([int(str(k), 0) for k in req["keysyms"]])
        return {}
    if cmd == "type":
        for ch in req["text"]:
            screen.key(ord(ch))
            time.sleep(req.get("delay", 0.06))
        return {}
    if cmd == "wait":
        time.sleep(req["ms"] / 1000)
        return {}
    if cmd == "record":
        recorder = Recorder(screen, req["path"], req.get("fps", 30), req.get("width"))
        return {}
    if cmd == "stop":
        frames = recorder.stop() if recorder else 0
        recorder = None
        return {"frames": frames}
    if cmd == "quit":
        if recorder:
            recorder.stop()
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        return {"quit": True}
    raise ValueError(f"unknown command {cmd}")


if os.path.exists(sock_path):
    os.unlink(sock_path)
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(sock_path)
server.listen(4)
while True:
    conn, _ = server.accept()
    try:
        req = json.loads(conn.makefile().readline())
        reply = {"ok": True, **handle(req)}
    except Exception as e:  # report back instead of dying, the launcher keeps running
        reply = {"ok": False, "error": repr(e)}
    reply["running"] = proc.poll() is None
    conn.sendall((json.dumps(reply) + "\n").encode())
    conn.close()
    if reply.get("quit"):
        break
os.unlink(sock_path)
