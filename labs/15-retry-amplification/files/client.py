"""Count original requests, client attempts and backend work separately."""
import argparse
import urllib.error
import urllib.request
from pathlib import Path


def run(phase, retries, workspace, url='http://127.0.0.1:8090/work', count=20):
    # Ignore ambient proxy settings: the experiment is explicitly local.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    attempts = successes = 0
    for number in range(count):
        for _ in range(retries + 1):
            attempts += 1
            request = urllib.request.Request(url, headers={'X-Lab-Request': f'{phase}-{number}'})
            try:
                with opener.open(request, timeout=2) as response:
                    if response.status == 200:
                        successes += 1
                        break
            except urllib.error.HTTPError as exc:
                if exc.code != 503:
                    raise RuntimeError(f'Unexpected HTTP {exc.code}; inspect the fixture') from exc
                exc.close()
            # Connection failures are fixture failures, not the intended 503 fault.
    arrivals = sum(
        line.startswith(f'{phase}-')
        for port in (9001, 9002)
        for line in (workspace / f'arrivals-{port}.log').read_text().splitlines()
    )
    print(f'phase={phase} original={count} client_attempts={attempts} '
          f'backend_arrivals={arrivals} amplification={arrivals/count:.2f} '
          f'successes={successes}/{count}', flush=True)
    return successes, arrivals


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('baseline', 'fault', 'recovered'))
    parser.add_argument('retries', type=int, choices=(0, 1))
    args = parser.parse_args()
    successes, _ = run(args.phase, args.retries, Path(__file__).resolve().parent)
    if args.phase != 'fault' and successes != 20:
        raise SystemExit('Baseline/recovery failed; stop before interpreting the experiment')
