"""Create live children until the pids cgroup refuses a fork, then reap them."""
import os
import signal
import sys
import time
from pathlib import Path

CGROUP = Path('/sys/fs/cgroup')


def gauge():
    return CGROUP.joinpath('pids.current').read_text().strip(), CGROUP.joinpath('pids.max').read_text().strip()


requested = int(sys.argv[1])
children = []
failure = 'none'
for _ in range(requested):
    try:
        pid = os.fork()
    except OSError as error:
        failure = f'errno={error.errno} {error.strerror}'
        break
    if pid == 0:
        time.sleep(20)
        os._exit(0)
    children.append(pid)

current, maximum = gauge()
print(f'requested={requested} created={len(children)} fork_error={failure}', flush=True)
print(f'pids.current={current} pids.max={maximum}', flush=True)
for pid in children:
    os.kill(pid, signal.SIGKILL)
for pid in children:
    os.waitpid(pid, 0)
print(f'pids.current_after_reaping={gauge()[0]}', flush=True)
