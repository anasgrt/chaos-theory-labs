"""A minimal container init as PID 1: stay alive and reap every inherited orphan."""
import os
import signal
import time

signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
print(f'init pid={os.getpid()} reaping=yes', flush=True)
while True:
    try:
        pid, status = os.waitpid(-1, os.WNOHANG)
    except ChildProcessError:
        pid = 0  # nothing has been inherited yet
    if pid == 0:
        time.sleep(0.2)
        continue
    print(f'reaped pid={pid} status={status}', flush=True)
