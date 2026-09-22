"""Report the identity, capabilities and visibility this container actually has."""
import os
from pathlib import Path

STATUS_KEYS = ('CapPrm', 'CapEff', 'CapBnd', 'NoNewPrivs', 'Seccomp')


def status():
    values = {}
    for line in Path('/proc/self/status').read_text().splitlines():
        key, _, value = line.partition(':')
        if key in STATUS_KEYS:
            values[key] = value.strip()
    return values


def capability_probe():
    """Changing a file's owner needs CAP_CHOWN, so it fails without that capability."""
    try:
        target = Path('/tmp/ce-lab16-chown-probe')
        target.write_text('probe\n')
        os.chown(target, 1, 1)
        target.unlink()
        return 'chown allowed'
    except OSError as error:
        return f'chown refused: {type(error).__name__}: {error.strerror}'


def write_probe(path):
    try:
        target = Path(path) / 'ce-lab16-write-probe'
        target.write_text('probe\n')
        target.unlink()
        return 'writable'
    except OSError as error:
        return f'{type(error).__name__}: {error.strerror}'


pids = sorted(int(entry.name) for entry in Path('/proc').iterdir() if entry.name.isdigit())
try:
    pid1 = Path('/proc/1/cmdline').read_bytes().decode().replace('\0', ' ').strip()[:60]
except OSError as error:
    pid1 = f'unreadable ({error.strerror})'

values = status()
print(f'uid={os.getuid()} gid={os.getgid()}')
print(' '.join(f'{key}={values.get(key, "?")}' for key in STATUS_KEYS))
print(f'visible_pids={len(pids)} highest_pid={pids[-1]} pid1_cmdline={pid1}')
print(f'dev_entries={len(list(Path("/dev").iterdir()))} block_devices={sorted(p.name for p in Path("/dev").glob("[sv]d*"))}')
print(f'write_root={write_probe("/")} write_tmp={write_probe("/tmp")}')
print(f'capability_check={capability_probe()}')
