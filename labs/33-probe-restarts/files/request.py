"""One bounded HTTP observation from the client Pod."""
import sys
import time
import urllib.error
import urllib.request

started = time.monotonic()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with opener.open('http://probe-web:8080/', timeout=3) as reply:
        print(f'HTTP {reply.status}; body={reply.read().decode().strip()}')
except (urllib.error.URLError, TimeoutError, OSError) as error:
    print(f'HTTP request failed: {error}', file=sys.stderr)
    sys.exit(1)
finally:
    print(f'elapsed_seconds={time.monotonic() - started:.3f}')
