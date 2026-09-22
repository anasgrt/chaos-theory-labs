"""Time fresh HTTP availability; distinguish deadline misses from checker errors."""
import argparse
import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
KUBECTL = ['kubectl', f'--kubeconfig={WORKSPACE}/kubeconfig',
           '--context=kind-lab12', '--namespace=chaos-labs', '--request-timeout=5s']


def k(*args, timeout=15):
    return subprocess.run(KUBECTL + list(args), check=True, capture_output=True,
                          text=True, timeout=timeout).stdout


def cleanup():
    k('delete', '-f', str(WORKSPACE / 'startup.yaml'), '--ignore-not-found',
      '--wait=true', '--timeout=30s', '--grace-period=1', '--request-timeout=0', timeout=40)


def probe_until(url, start, budget, clock=time.monotonic, sleep=time.sleep, opener=None):
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = start + budget
    while (remaining := deadline - clock()) > 0:
        try:
            with opener.open(url, timeout=min(1, remaining)) as response:
                elapsed = clock() - start
                if response.status == 200 and elapsed <= budget:
                    return 1, elapsed
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        sleep(min(0.25, max(0, deadline - clock())))
    return 0, clock() - start


def diagnostics(trial):
    """Capture evidence before deletion; unavailable reads remain explicit errors."""
    result = {'trial': trial}
    queries = {
        'pod': ('get', 'pod', 'startup-check'),
        'service': ('get', 'service', 'startup-check'),
        'endpointslices': ('get', 'endpointslices', '-l', 'kubernetes.io/service-name=startup-check'),
        'events': ('get', 'events', '--field-selector', 'involvedObject.kind=Pod,involvedObject.name=startup-check'),
    }
    for name, query in queries.items():
        try:
            result[name] = json.loads(k(*query, '-o', 'json'))
        except (subprocess.SubprocessError, OSError, ValueError) as exc:
            result[name] = {'diagnostic_error': str(exc), 'detail': getattr(exc, 'stderr', None)}
    # Events can outlive a deleted Pod with the same name. Match this trial's UID.
    uid = result['pod'].get('metadata', {}).get('uid')
    if 'items' in result['events']:
        if uid:
            result['events']['items'] = [event for event in result['events']['items']
                                        if event.get('involvedObject', {}).get('uid') == uid]
        else:
            result['events'] = {'diagnostic_error': 'Pod UID unavailable; cannot attribute events to this trial'}
    return result


def run(count):
    evidence = WORKSPACE / 'diagnostics'
    evidence.mkdir(exist_ok=True)
    for previous in evidence.glob('run-*.json'):
        previous.unlink()
    info = subprocess.run(['docker', 'inspect', 'lab12-control-plane'], check=True,
                          capture_output=True, text=True, timeout=10)
    node_ip = json.loads(info.stdout)[0]['NetworkSettings']['Networks']['kind']['IPAddress']
    metrics = WORKSPACE / 'metrics'
    metrics.mkdir(exist_ok=True)
    try:
        for number in range(1, count + 1):
            cleanup()
            start = time.monotonic()
            k('apply', '-f', str(WORKSPACE / 'startup.yaml'))
            ok, elapsed = probe_until(f'http://{node_ip}:30090/', start, 30)
            timestamp = time.time()
            snapshot = diagnostics({'number': number, 'success': ok, 'elapsed_seconds': elapsed,
                                    'timestamp_seconds': timestamp})
            record = evidence / f'run-{number}.json'
            temporary_record = record.with_suffix('.json.tmp')
            temporary_record.write_text(json.dumps(snapshot, indent=2) + '\n', encoding='utf-8')
            os.replace(temporary_record, record)
            print(f'run={number} success={ok} elapsed={elapsed:.3f}s', flush=True)
            temporary = metrics / 'start.prom.tmp'
            temporary.write_text(f'ce_start_success {ok}\nce_start_seconds {elapsed:.3f}\n'
                                 f'ce_last_run_timestamp_seconds {timestamp:.6f}\n')
            os.replace(temporary, metrics / 'start.prom')
    finally:
        cleanup()


def interrupted(*_):
    raise KeyboardInterrupt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('count', nargs='?', type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.count <= 20:
        parser.error('Use 1–20 trials')
    signal.signal(signal.SIGTERM, interrupted)
    try:
        run(args.count)
    except (KeyboardInterrupt, subprocess.SubprocessError, OSError) as exc:
        raise SystemExit(f'Checker did not complete cleanly: {exc}')
