"""Report this container's process table, orphan parentage and pids counters."""
from pathlib import Path

CGROUP = Path('/sys/fs/cgroup')


def counter(name):
    try:
        return CGROUP.joinpath(name).read_text().strip()
    except OSError as error:
        return f'unreadable ({error.strerror})'


def process(pid):
    """Return (comm, state, ppid) from /proc/PID/stat, which quotes comm in parentheses."""
    stat = Path(f'/proc/{pid}/stat').read_text()
    start, end = stat.index('('), stat.rindex(')')
    fields = stat[end + 2:].split()
    return stat[start + 1:end], fields[0], int(fields[1])


rows = []
for entry in Path('/proc').iterdir():
    if not entry.name.isdigit():
        continue
    try:
        comm, state, ppid = process(entry.name)
    except (OSError, ValueError):
        continue  # the process exited while this report was being written
    rows.append((int(entry.name), ppid, state, comm))

rows.sort()
zombies = [row for row in rows if row[2] == 'Z']
orphaned_zombies = [row for row in zombies if row[1] == 1]
pid1_command = Path('/proc/1/cmdline').read_bytes().decode().replace('\0', ' ').strip()
if len(pid1_command) > 60:
    pid1_command = pid1_command[:57] + '...'
print(f'pid1_comm={Path("/proc/1/comm").read_text().strip()} pid1_cmdline={pid1_command}')
print(f'processes={len(rows)} zombies={len(zombies)} zombies_reparented_to_pid1={len(orphaned_zombies)}')
print(f'pids.current={counter("pids.current")} pids.max={counter("pids.max")}')
for pid, ppid, state, comm in rows[:6]:
    print(f'  pid={pid:<6} ppid={ppid:<6} state={state} comm={comm}')
for pid, ppid, state, comm in zombies[:3]:
    print(f'  zombie pid={pid:<6} ppid={ppid:<6} state={state} comm={comm}')
