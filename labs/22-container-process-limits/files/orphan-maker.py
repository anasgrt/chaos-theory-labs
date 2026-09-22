"""Create short-lived children and exit first, so PID 1 inherits them as orphans."""
import os
import sys
import time

requested = int(sys.argv[1])
made = 0
for _ in range(requested):
    pid = os.fork()
    if pid == 0:
        time.sleep(0.5)  # outlive this maker so PID 1 becomes the parent
        os._exit(0)
    made += 1
print(f'maker_pid={os.getpid()} orphans_started={made}', flush=True)
