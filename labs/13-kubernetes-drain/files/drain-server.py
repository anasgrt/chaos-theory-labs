"""HTTP server with a measurable request duration and two shutdown behaviours."""
import os
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DURATION = float(os.environ.get('REQUEST_SECONDS', '2'))
MODE = os.environ.get('SHUTDOWN', 'graceful')
POD = os.environ.get('POD_NAME', 'unknown')
inflight = 0
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def do_GET(self):
        global inflight
        if self.path == '/healthz':
            self.reply(b'ok\n')  # readiness must not wait for the work path
            return
        with lock:
            inflight += 1
        try:
            time.sleep(DURATION)
            self.reply(f'{POD}\n'.encode())
        finally:
            with lock:
                inflight -= 1

    def reply(self, body):
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(('0.0.0.0', 8080), Handler)
server.daemon_threads = False  # server_close joins the threads still answering


def stop(signum, _frame):
    print(f'sigterm received inflight={inflight} shutdown={MODE}', flush=True)
    if MODE == 'abrupt':
        # Leave immediately, without finishing the requests being served. This
        # stands in for an application with no shutdown handling: as PID 1 in a
        # container the kernel discards a default-disposition SIGTERM, so the
        # exit is made explicit here. 143 is the conventional 128 + SIGTERM.
        os._exit(143)
    threading.Thread(target=server.shutdown, daemon=True).start()


signal.signal(signal.SIGTERM, stop)
print(f'ready pod={POD} request_seconds={DURATION} shutdown={MODE}', flush=True)
server.serve_forever()
print('stopped accepting new connections', flush=True)
server.server_close()
print(f'exited cleanly inflight={inflight}', flush=True)
