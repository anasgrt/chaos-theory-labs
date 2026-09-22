"""A visible two-second cleanup path for the signal-delivery experiment."""
import os
import signal
import time
from pathlib import Path


def stop(signum, _frame):
    print(f'received={signum} cleanup-start', flush=True)
    time.sleep(2)
    Path('/cleanup-complete').write_text('completed\n')
    print('cleanup-complete', flush=True)
    raise SystemExit(0)


signal.signal(signal.SIGTERM, stop)
print(f'ready pid={os.getpid()} ppid={os.getppid()}', flush=True)
while True:
    time.sleep(1)
