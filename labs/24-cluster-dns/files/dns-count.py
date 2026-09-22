"""Resolve each name and report the CoreDNS queries and time it actually cost."""
import socket
import sys
import time
import urllib.request

endpoints = [endpoint for endpoint in sys.argv[1].split(',') if endpoint]
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def requests_total():
    """Sum coredns_dns_requests_total across every replica, or None when unreachable."""
    if not endpoints:
        return None  # the resolver Service has no replica exposing metrics
    total = 0.0
    for endpoint in endpoints:
        try:
            with opener.open(f'http://{endpoint}/metrics', timeout=5) as response:
                payload = response.read().decode()
        except OSError:
            return None
        for line in payload.splitlines():
            if line.startswith('coredns_dns_requests_total{'):
                total += float(line.rsplit(' ', 1)[1])
    return total


def difference(before, after):
    if before is None or after is None:
        return 'unavailable'
    return f'{after - before:.0f}'


for name in sys.argv[2:]:
    before = requests_total()
    started = time.monotonic()
    try:
        outcome = 'addresses=' + str(sorted({info[4][0] for info in socket.getaddrinfo(name, 80)}))
    except OSError as error:
        outcome = f'error={type(error).__name__}: {error}'
    elapsed = (time.monotonic() - started) * 1000
    print(f'name={name} queries={difference(before, requests_total())} elapsed_ms={elapsed:.0f} {outcome}', flush=True)
