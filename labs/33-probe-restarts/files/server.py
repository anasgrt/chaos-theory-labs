"""A slow-starting service with independent readiness and progress faults."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import time


def response(path):
    if Path('/tmp/stalled').exists() and path in ('/', '/livez'):
        return 503, b'progress stalled\n'
    if path == '/readyz' and (Path('/tmp/unready').exists() or Path('/tmp/stalled').exists()):
        return 503, b'not ready\n'
    return 200, b'OK\n'


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, body = response(self.path)
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    print('starting: initialization takes 15 seconds', flush=True)
    time.sleep(15)
    print('listening: initialization complete', flush=True)
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
