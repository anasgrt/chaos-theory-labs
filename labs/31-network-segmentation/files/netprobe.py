"""One request or one lookup, timed, with the failure shape named."""
import socket
import sys
import time
import urllib.error
import urllib.request

BUDGET = 5.0


def http(url):
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=BUDGET) as response:
            return f'ok status={response.status}', started
    except urllib.error.HTTPError as error:
        return f'http_error status={error.code}', started
    except Exception as error:  # refused, dropped, or unresolved
        name = type(error).__name__
        reason = getattr(error, 'reason', error)
        return f'failed {name} reason={reason}', started


def resolve(name):
    started = time.monotonic()
    try:
        return f'resolved {socket.gethostbyname(name)}', started
    except OSError as error:
        return f'failed {type(error).__name__} errno={error.errno}', started


def main(argv):
    if len(argv) != 3 or argv[1] not in ('http', 'dns'):
        print('usage: netprobe.py http URL | netprobe.py dns NAME', file=sys.stderr)
        return 2
    action, target = argv[1], argv[2]
    result, started = http(target) if action == 'http' else resolve(target)
    print(f'{action} {target} -> {result} elapsed_ms={int((time.monotonic() - started) * 1000)}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
