"""Report every surface through which this container can read its Secret."""
import os
import pathlib
import sys

MOUNT = pathlib.Path('/etc/app-credentials/password')


def environment():
    value = os.environ.get('APP_PASSWORD')
    return value if value is not None else 'absent'


def from_proc():
    """The same variable as any other process in this container would read it."""
    try:
        entries = pathlib.Path('/proc/1/environ').read_bytes().split(b'\0')
    except OSError as error:
        return f'unreadable ({error.strerror})'
    for entry in entries:
        name, _, value = entry.decode('utf-8', 'replace').partition('=')
        if name == 'APP_PASSWORD':
            return value
    return 'absent'


def mounted():
    if not MOUNT.exists():
        return 'absent', 'absent', 'absent'
    resolved = MOUNT.resolve()
    mode = oct(resolved.stat().st_mode & 0o777)[2:]
    return MOUNT.read_text().strip(), mode, str(resolved)


def main():
    value, mode, resolved = mounted()
    print(f'env_var={environment()}')
    print(f'proc_1_environ={from_proc()}')
    print(f'mounted_file={value}')
    print(f'mounted_mode={mode}')
    print(f'mounted_target={resolved}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
