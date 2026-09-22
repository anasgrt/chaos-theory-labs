"""Small HTTP dependency: /healthz is a control; /work is the measured path."""
import argparse
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def serve(port, workspace):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            status = 200
            if self.path == '/work':
                status = 503 if (workspace / 'fail').exists() else 200
                with lock, (workspace / f'arrivals-{port}.log').open('a') as log:
                    log.write(f'{self.headers.get("X-Lab-Request", "unknown")} {status}\n')
            elif self.path != '/healthz':
                status = 404
            body = f'{status}\n'.encode()
            self.send_response(status)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(('127.0.0.1', port), Handler) as server:
        server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('port', type=int)
    args = parser.parse_args()
    serve(args.port, Path(__file__).resolve().parent)
