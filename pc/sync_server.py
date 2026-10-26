"""
Local Wi-Fi Synchronization Server for Lockin-Inator PC.
Provides REST and Server-Sent Event (SSE) endpoints on port 8765,
plus UDP broadcast beacons on port 8766 for automatic device discovery
across Android, Microsoft Edge, and PC.
"""
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional

DEFAULT_HTTP_PORT = 8765
DEFAULT_UDP_BEACON_PORT = 8766


def get_local_ip() -> str:
    """Detects the current machine's active local LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class SyncServerHandler(BaseHTTPRequestHandler):
    server: "SyncHTTPServer"  # Type hint for custom server attribute

    def log_message(self, format, *args):
        # Suppress noisy standard HTTP access logs
        pass

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def finish(self):
        try:
            super().finish()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            pass

    def do_GET(self):
        try:
            if self.path.startswith("/api/status"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()

                status_data = self.server.get_status_dict()
                self.wfile.write(json.dumps(status_data).encode("utf-8"))

            elif self.path.startswith("/api/stream"):
                # Server-Sent Events (SSE) live push stream
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self._send_cors_headers()
                self.end_headers()

                client_queue = self.server.register_sse_client()
                try:
                    # Send immediate initial status
                    init_data = json.dumps(self.server.get_status_dict())
                    self.wfile.write(f"data: {init_data}\n\n".encode("utf-8"))
                    self.wfile.flush()

                    while self.server.running:
                        try:
                            msg = client_queue.get(timeout=1.0)
                            self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                            self.wfile.flush()
                        except Exception:
                            # Keep-alive heartbeat comment every few seconds
                            self.wfile.write(b": keep-alive\n\n")
                            self.wfile.flush()
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                    pass
                finally:
                    self.server.unregister_sse_client(client_queue)
            else:
                self.send_response(404)
                self._send_cors_headers()
                self.end_headers()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            pass

    def do_POST(self):
        try:
            if self.path.startswith("/api/action"):
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)

                try:
                    payload = json.loads(post_data.decode("utf-8"))
                except Exception:
                    payload = {}

                action = payload.get("action", "")
                duration = payload.get("duration_minutes", None)

                success = self.server.dispatch_action(action, duration)

                self.send_response(200 if success else 400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()

                resp = {"success": success, "status": self.server.get_status_dict()}
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            else:
                self.send_response(404)
                self._send_cors_headers()
                self.end_headers()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            pass


class SyncHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, RequestHandlerClass, sync_manager):
        super().__init__(server_address, RequestHandlerClass)
        self.sync_manager = sync_manager
        self.running = True
        self.sse_clients = []
        self._lock = threading.Lock()

    def handle_error(self, request, client_address):
        import sys
        exc_type, exc_value, _ = sys.exc_info()
        if exc_type in (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            return
        super().handle_error(request, client_address)

    def get_status_dict(self):
        return self.sync_manager.get_status()

    def dispatch_action(self, action: str, duration: Optional[int]) -> bool:
        return self.sync_manager.handle_action(action, duration)

    def register_sse_client(self):
        import queue
        q = queue.Queue(maxsize=10)
        with self._lock:
            self.sse_clients.append(q)
        return q

    def unregister_sse_client(self, q):
        with self._lock:
            if q in self.sse_clients:
                self.sse_clients.remove(q)

    def broadcast_state(self, status_dict):
        msg = json.dumps(status_dict)
        with self._lock:
            for q in list(self.sse_clients):
                try:
                    q.put_nowait(msg)
                except Exception:
                    pass


class SyncManager:
    def __init__(self, port=DEFAULT_HTTP_PORT, udp_port=DEFAULT_UDP_BEACON_PORT):
        self.port = port
        self.udp_port = udp_port
        self.local_ip = get_local_ip()
        self.http_server: Optional[SyncHTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.beacon_thread: Optional[threading.Thread] = None
        self.running = False

        self._status_getter: Optional[Callable[[], dict]] = None
        self._action_callback: Optional[Callable[[str, Optional[int]], bool]] = None

    def set_status_provider(self, provider: Callable[[], dict]):
        self._status_getter = provider

    def set_action_callback(self, callback: Callable[[str, Optional[int]], bool]):
        self._action_callback = callback

    def get_status(self) -> dict:
        if self._status_getter:
            data = self._status_getter()
        else:
            data = {"state": "IDLE", "remaining_seconds": 0}
        data["server_ip"] = self.local_ip
        data["port"] = self.port
        data["timestamp"] = int(time.time())
        return data

    def handle_action(self, action: str, duration: Optional[int]) -> bool:
        if self._action_callback:
            return self._action_callback(action, duration)
        return False

    def start(self):
        if self.running:
            return
        self.running = True
        self.local_ip = get_local_ip()

        try:
            self.http_server = SyncHTTPServer(("0.0.0.0", self.port), SyncServerHandler, self)
            self.server_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            self.server_thread.start()
        except Exception as e:
            print(f"[SyncServer] Failed to bind HTTP server on port {self.port}: {e}")
            self.running = False
            return

        # Start UDP Discovery Beacon
        self.beacon_thread = threading.Thread(target=self._run_udp_beacon, daemon=True)
        self.beacon_thread.start()
        print(f"[SyncServer] Running at http://{self.local_ip}:{self.port}")

    def _run_udp_beacon(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        beacon_data = json.dumps({
            "service": "lockin-inator-sync",
            "ip": self.local_ip,
            "port": self.port
        }).encode("utf-8")

        while self.running:
            try:
                sock.sendto(beacon_data, ("<broadcast>", self.udp_port))
            except Exception:
                pass
            time.sleep(2.5)

        sock.close()

    def broadcast_update(self):
        if self.http_server:
            self.http_server.broadcast_state(self.get_status())

    def stop(self):
        self.running = False
        if self.http_server:
            self.http_server.running = False
            self.http_server.shutdown()
            self.http_server = None
