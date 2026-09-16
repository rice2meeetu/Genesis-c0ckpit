#!/usr/bin/env python3
import atexit
import fcntl
import json
import os
import pty
import select
import signal
import struct
import sys
import termios
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
pid = None
master_fd = None
lock = threading.Lock()

def spawn_shell():
    global pid, master_fd
    pid, master_fd = pty.fork()
    if pid == 0:
        os.chdir(os.path.expanduser("~"))
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"
        env["PS1"] = r"\u@\h:\w\$ "
        os.execvpe("/bin/bash", ["/bin/bash", "--noprofile", "--norc", "-i"], env)

    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 42, 120, 0, 0))

def shell_alive():
    global pid
    if pid is None:
        return False
    try:
        result, _ = os.waitpid(pid, os.WNOHANG)
        return result == 0
    except ChildProcessError:
        return False

def ensure_shell():
    if not shell_alive():
        spawn_shell()

def cleanup():
    global pid
    if pid:
        try:
            os.kill(pid, signal.SIGHUP)
        except Exception:
            pass

atexit.register(cleanup)

class Handler(BaseHTTPRequestHandler):

    # GENESIS_BRIDGE_CORS_FIX_V1
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        return

    def cors(self):
        origin = self.headers.get("Origin")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            ensure_shell()
            payload = json.dumps({"ok": True, "shell": "/bin/bash", "pid": pid}).encode()
            self.send_response(200)
            self.cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if self.path == "/read":
            ensure_shell()
            chunks = []
            with lock:
                while True:
                    try:
                        ready, _, _ = select.select([master_fd], [], [], 0)
                        if not ready:
                            break
                        data = os.read(master_fd, 65536)
                        if not data:
                            break
                        chunks.append(data)
                    except (BlockingIOError, OSError):
                        break
            payload = b"".join(chunks)
            self.send_response(200)
            self.cors()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_response(404)
        self.cors()
        self.end_headers()

    def do_POST(self):
        if self.path != "/write":
            self.send_response(404)
            self.cors()
            self.end_headers()
            return
        ensure_shell()
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            obj = json.loads(raw.decode("utf-8"))
            data = str(obj.get("data", "")).encode("utf-8")
            with lock:
                os.write(master_fd, data)
            payload = b'{"ok":true}'
            self.send_response(200)
            self.cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            payload = json.dumps({"ok": False, "error": str(exc)}).encode()
            self.send_response(500)
            self.cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

spawn_shell()
server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
print(f"GENESIS terminal bridge listening on http://127.0.0.1:{PORT}", flush=True)
server.serve_forever()
