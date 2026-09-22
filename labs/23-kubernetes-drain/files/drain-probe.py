"""Send a steady concurrent request stream and report outcomes second by second."""
import sys
import threading
import time
import urllib.request

url, seconds, rate = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
start = time.monotonic()
lock = threading.Lock()
buckets = {}
failures = []


def once():
    sent = time.monotonic() - start
    try:
        with opener.open(url, timeout=10) as response:
            response.read()
        ok, detail = response.status == 200, f'status {response.status}'
    except Exception as error:  # any transport or HTTP failure is a failed request
        ok, detail = False, f'{type(error).__name__}: {error}'
    with lock:
        bucket = buckets.setdefault(int(sent), [0, 0])
        bucket[0 if ok else 1] += 1
        if not ok:
            failures.append((round(sent, 2), detail))


threads = []
while time.monotonic() - start < seconds:
    worker = threading.Thread(target=once)
    worker.start()
    threads.append(worker)
    time.sleep(1.0 / rate)
for worker in threads:
    worker.join()

succeeded = sum(bucket[0] for bucket in buckets.values())
failed = sum(bucket[1] for bucket in buckets.values())
print(f'url={url} requests={succeeded + failed} ok={succeeded} failed={failed}')
for second in sorted(buckets):
    print(f'  t={second:>2}s ok={buckets[second][0]:>3} failed={buckets[second][1]:>3}')
for moment, detail in sorted(failures)[:8]:
    print(f'  first failures t={moment}s {detail}')
