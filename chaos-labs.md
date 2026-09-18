# Chaos labs — understand the result

Each lab connects one question to a controlled comparison. Read the theory, predict the result, run the core procedure, and explain your observations before opening the solution. The explanations come from `chaos-theory.md`; the commands adapt them to this repository's fixtures.

## Start here

1. From the Mac project folder, run `./up.sh` and complete Lab 00.
2. Prepare the chosen lab with `./ansible/run-lab.sh NN setup`, then check its baseline with `./ansible/run-lab.sh NN verify`. Setup prepares the fixture and supporting programs; it does not inject the fault. Rerunning setup resets the fixture.
3. Read `./ansible/run-lab.sh NN question`, which includes the core commands. Use `vagrant ssh` for the named VM terminals. Run commands in Bash without exit-on-error: some failures are deliberate observations.
4. Record your prediction, observed comparison and explanation. Then open the solution or run `./ansible/run-lab.sh NN solution`. Finish recovery and any optional work before `./ansible/run-lab.sh NN reset` on the Mac.

Stop if the baseline fails. A setup error, failed injector or missing measurement is not evidence of resilience. If the outcome differs from your prediction, check that the fault took effect and that recovery passed; report the result you actually observed. Expected timings and counts are not guarantees.

Use only the named targets in the disposable VM, one fault at a time. Keep another VM terminal available for cleanup. A stopped injector does not always remove its effect; use each lab's recovery procedure. Lab 00 establishes a snapshot as a fallback.

**Dependencies:** Labs 11–13 require Lab 10's `chaos` cluster. Lab 08 setup stops Lab 07's stack because both use port 8080. Lab 14 uses a separate `ha` cluster: remove `chaos` and allocate at least 16 GiB VM memory first, as described in README.md. Lab 16 is design only. Other labs use the shared Lab 00 environment.

**A complete answer:** what changed → the evidence → why the mechanism explains it → whether recovery passed. Use your own numbers and outputs. Optional comparisons are not completion requirements. Prepared scripts remain readable under `~/labs/labNN/`; understanding their implementation is optional unless it is the subject of the question.

## Labs

- [Lab 00: Prepare the learning environment](#lab-00)
- [Lab 01: A timeout makes a silent failure manageable](#lab-01)
- [Lab 02: Prove why a process was killed](#lab-02)
- [Lab 03: Restart policies have limits](#lab-03)
- [Lab 04: CPU contention and a quota](#lab-04)
- [Lab 05: A container is several Linux mechanisms](#lab-05)
- [Lab 06: Separate containers can share a full filesystem](#lab-06)
- [Lab 07: Tools can act through a shared namespace](#lab-07)
- [Lab 08: A syscall error tests application handling](#lab-08)
- [Lab 09: A syscall denial need not crash the process](#lab-09)
- [Lab 10: Replacing a Pod is not the same as uninterrupted service](#lab-10)
- [Lab 11: Health depends on what you test](#lab-11)
- [Lab 12: Test whether the checker detects failure](#lab-12)
- [Lab 13: Losing supervision does not stop the process](#lab-13)
- [Lab 14: Quorum controls writes, not every application request](#lab-14)
- [Lab 15: Retries can multiply work](#lab-15)
- [Lab 16: Design one clear experiment](#lab-16)

<a id="lab-00"></a>

## Lab 00 — Prepare the learning environment

**Question:** Which checks establish a usable baseline before you inject a fault?

A baseline is the working state you compare with a fault. If the environment is already broken, a later failure cannot be attributed to the experiment. Check the required tools before introducing any fault.

These labs use Linux namespaces and cgroup v2 to isolate processes and limit resources. Record the software versions because interfaces and defaults can differ. A disposable VM contains the experiments, and a snapshot gives you a recovery point if cleanup fails. Saving a snapshot establishes that the restore point exists; it does not test restoration.

**Source:** chaos-theory.md: §§1.3, 2.1, 2.5; Appendix A.

**In this lab:** Use the Ubuntu VM prepared by ./up.sh. The shared checks require cgroup v2, Docker, Compose and at least 60 GiB total root filesystem capacity.

**Predict:** If a prerequisite already fails, can a later failure tell you anything about the injected fault?

1. Check cgroup v2, Docker, Compose and filesystem capacity. Resolve failed checks before continuing.
2. Record the book commit, tool versions and image digests; locally built images may have no registry digest.
3. From the Mac host, save snapshot 01-tools and confirm it is listed.

**Explain the result:** Name the checks that passed, the recorded environment version and the listed recovery snapshot. Explain why a failed baseline blocks a meaningful comparison.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 00 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Check the kernel, cgroup, Docker and disk baseline** — VM terminal 1

```bash
uname -m
stat -fc %T /sys/fs/cgroup
systemd --version | head -1
docker info --format 'driver={{.CgroupDriver}} cgroups={{.CgroupVersion}}'
docker run --rm hello-world
docker compose version
df -h /
```

**2. Review the recorded source commit, versions, helpers and image digests** — VM terminal 1

```bash
cat ~/labs/book-commit.txt
git -C ~/labs/book rev-parse HEAD
cat ~/labs/versions.txt
source ~/labs/common.sh
type cg measure
for image in mysql:8.4 wordpress:6-apache python:3.12-slim ubuntu:24.04 busybox:1.36 nginx:1.27 ghcr.io/shopify/toxiproxy:2.12.0 bloomberg/goldpinger:v3.11.3; do
  printf '%s ' "$image"
  docker image inspect "$image" --format '{{json .RepoDigests}}'
done
```

**3. Save the tools snapshot** — Mac host, project folder

```bash
vagrant snapshot save 01-tools
vagrant snapshot list
```

**Recovery check:** Prerequisite checks pass and snapshot 01-tools is listed.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

A usable baseline lets you attribute later changes to the fault instead of a broken setup. Version records make results interpretable; the snapshot supplies a recovery point.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** cgroup2fs, Docker cgroups=2, a successful hello-world run, a working Compose plugin and at least 60 GiB on /.

**Step 2:** The commit is 3e3ee64db71f51a5e9f79af8562dd4aa913a0e71. A locally built image (Goldpinger on ARM64) has no registry digest.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 00 reset`.

<a id="lab-01"></a>

## Lab 01 — A timeout makes a silent failure manageable

**Question:** Why does the exception handler run after refusal but not while packets are silently dropped?

An exception handler runs only after an operation raises an error. A refused TCP connection produces an error promptly. Silently discarded packets provide no reply, so the connection attempt can keep waiting before the handler is reached.

An application timeout limits that wait and lets the operation raise an error the handler can catch. A connect timeout bounds connection establishment; a read timeout bounds waiting after connection. The external watchdog instead terminates the test process. It keeps the experiment short but does not make the application handle the dependency failure.

**Source:** chaos-theory.md: §1.5 and Experiment Card 1.1.

**In this lab:** One ce-lab01 firewall rule targets TCP 127.0.0.1:6379. All fault runs use a five-second watchdog; TIMEOUT=0.5 sets the client timeouts.

**Predict:** Predict which of the three attempts reaches the handler: REJECT, DROP, and DROP with a 0.5-second timeout.

1. Confirm the prepared client succeeds without a fault.
2. Run the prepared comparison and record each result and wait time.
3. Confirm the client succeeds after cleanup. Explain which limit belongs to the application and which belongs to the test.

**Explain the result:** For each attempt, state whether the handler ran and what ended the wait. Use those observations to explain why catching errors alone does not bound waiting.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 01 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Check the Redis baseline** — VM terminal 1

```bash
cd ~/labs/lab01
redis-cli ping
python3 client.py
```

**2. Predict, run, then prove recovery** — VM terminal 1

```bash
cd ~/labs/lab01
bash run.sh
python3 client.py
sudo iptables -S OUTPUT | grep ce-lab01; echo "grep exit=$? (1 means no lab rule remains)"
```

**3. Manual rule removal, only if run.sh was killed** — VM terminal 2

```bash
sudo iptables -D OUTPUT -p tcp -d 127.0.0.1 --dport 6379 -m comment --comment ce-lab01 -j DROP
sudo iptables -D OUTPUT -p tcp -d 127.0.0.1 --dport 6379 -m comment --comment ce-lab01 -j REJECT --reject-with tcp-reset
python3 ~/labs/lab01/client.py
```

**Recovery check:** The client succeeds again and no ce-lab01 rule remains.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

REJECT should reach the handler quickly. DROP without an application timeout should reach the five-second watchdog instead. With TIMEOUT=0.5, the client should handle the timeout near half a second. The handler needs an error; it does not create a time limit.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** PONG, then OK True.

**Step 2:** REJECT prints DEGRADED ConnectionError within milliseconds. DROP without a timeout prints nothing and is stopped by the external watchdog (exit=124). DROP with TIMEOUT=0.5 prints DEGRADED TimeoutError near 0.5 s. The ce-lab01 rule shows pkts above 0. The final client prints OK True.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 01 reset`.

<a id="lab-02"></a>

## Lab 02 — Prove why a process was killed

**Question:** Why is exit status 137 insufficient to diagnose an OOM kill?

SIGKILL stops a process without allowing a handler to run. Bash commonly reports death by SIGKILL as 137: 128 plus signal number 9. That status describes how the process ended, not why the signal was sent. A program can also explicitly return 137, so the number alone cannot establish the cause.

A cgroup memory limit restricts a group even when the VM has free memory elsewhere. If its memory demand cannot be satisfied, the kernel may kill a process to reclaim memory. Match the unit result and kernel log to the same process and time window to distinguish that event from an ordinary kill or the runtime limit expiring.

**Source:** chaos-theory.md: §2.3; optional memory comparison: §3.3.4 and Experiment Card 5.4 (with its qualification).

**In this lab:** The allocator runs only in ce-lab02, with 128 MiB memory, no swap and a 20-second runtime bound.

**Predict:** Will a deliberate SIGKILL and a memory-limit kill have different exit statuses? Which evidence can distinguish them?

1. Record the status of the deliberately killed process.
2. Run the memory-limited allocator and collect its unit and kernel logs.
3. Match the termination to its logged cause, then stop the allocator if needed.

**Explain the result:** Compare the known SIGKILL with the allocator result. Cite the matching log that identifies the allocator’s cause; status 137 alone is not enough.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 02 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Record a deliberate SIGKILL** — VM terminal 1

```bash
python3 -c 'import os,signal; os.kill(os.getpid(),signal.SIGKILL)'
echo "deliberate KILL exit=$?"
```

**2. Cause a cgroup-bounded OOM and collect unit plus kernel evidence** — VM terminal 1

```bash
since=$(date --iso-8601=seconds)
sudo systemd-run --unit=ce-lab02 --wait --collect \
  -p MemoryMax=128M -p MemorySwapMax=0 -p RuntimeMaxSec=20s \
  /usr/bin/python3 -c 'a=[]
while True: a.append(b"x"*1000000)'
sudo journalctl -u ce-lab02 --since "$since" --no-pager
sudo journalctl -k --since "$since" --no-pager | grep -iE 'oom|killed process'
sudo journalctl -u systemd-oomd --since "$since" --no-pager
```

**3. Stop the allocator if it remains active** — VM terminal 1

```bash
sudo systemctl stop ce-lab02.service 2>/dev/null || true
```

**Recovery check:** The allocator is stopped and its termination evidence has been recorded.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

The allocator should trigger a cgroup OOM kill before its runtime bound. Status 137 is consistent with SIGKILL, but only the matching memory-kill evidence explains why. If the logs show a runtime timeout or a userspace kill, report that cause instead.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** Bash normally reports 137. Here you know the cause because the program deliberately sent SIGKILL.

**Step 2:** The unit fails before the 20 s bound, with oom-kill in the unit log and a matching kernel line. An oomd entry means userspace acted instead.

</details>

<details>
<summary>Optional comparison — beyond the core question</summary>

Optional: compare other signal statuses, then virtual and resident memory. These examples extend the process-forensics lesson; they are not needed to distinguish a deliberate kill from OOM.

**1. Compare TERM, KILL and FPE exit statuses (interactive Bash, no set -e)** — VM terminal 1

```bash
sleep 60 & victim=$!; kill -TERM "$victim"; wait "$victim"; echo "TERM=$?"
sleep 60 & victim=$!; kill -KILL "$victim"; wait "$victim"; echo "KILL=$?"
python3 -c 'import os,signal; os.kill(os.getpid(),signal.SIGFPE)'; echo "FPE=$?"
```

Expected observation: TERM=143, KILL=137, FPE=136.

**2. Compare virtual size (VSZ) with touched memory (RSS)** — VM terminal 1

```bash
mkdir -p ~/labs/lab02 && cd ~/labs/lab02
cat > pages.py <<'PY'
import mmap, os, time
n=256*1024*1024
m=mmap.mmap(-1,n)
print('PID',os.getpid(),'mapped, not yet touched',flush=True)
time.sleep(10)
for offset in range(0,n,mmap.PAGESIZE): m[offset]=1
print('touched every page',flush=True)
time.sleep(10)
PY
python3 pages.py & victim=$!
for i in $(seq 1 20); do ps -p "$victim" -o pid,vsz,rss,comm; sleep 1; done
wait "$victim"
```

Expected observation: VSZ jumps by about 256 MiB at mapping; RSS rises only after "touched every page".

**3. Cleanup, only if something is still running** — VM terminal 1, same shell

```bash
sudo systemctl stop ce-lab02.service 2>/dev/null || true
kill -0 "$victim" 2>/dev/null && kill "$victim"
```

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 02 reset`.

<a id="lab-03"></a>

## Lab 03 — Restart policies have limits

**Question:** Why does one crash recover while a burst of crashes can leave the same service failed?

systemd can restart a crashed process, but each start is also subject to a rate limit. Enough starts within the configured interval exhaust the allowance and prevent further automatic recovery. A single crash can therefore recover while a rapid sequence leaves the service failed.

NGINX can continue serving through another usable backend. This can hide one failed instance from clients, but it cannot create capacity when both are unavailable. Compare backend state with HTTP results: a successful proxy response does not prove every backend recovered.

**Source:** chaos-theory.md: §§2.4–2.6 and Experiment Cards 2.1–2.2.

**In this lab:** A and B serve through NGINX. The core experiment targets only A: Restart=always, at most four starts per 20 seconds. B stays available during this comparison.

**Predict:** Predict A’s state after one kill and after six rapid kill attempts, with Restart=always unchanged.

1. Confirm the baseline and clear A’s old start-limit counter.
2. Kill A once; check its state after the restart.
3. Attempt six rapid kills; inspect A’s state and journal, then restore both units.

**Explain the result:** Compare A’s state after one crash and after the burst. Quote the start-limit evidence and explain why Restart=always did not guarantee another start.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 03 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Check baseline and clear the previous start counter** — VM terminal 1

```bash
sudo systemctl reset-failed ce-lab03-a
systemctl is-active ce-lab03-a ce-lab03-b
curl -fsS --max-time 3 http://127.0.0.1:8003/
```

**2. Kill A once and inspect its recovery** — VM terminal 1

```bash
sudo systemctl kill --kill-whom=main --signal=KILL ce-lab03-a
sleep 1
curl -fsS --max-time 3 http://127.0.0.1:8003/
systemctl show ce-lab03-a -p ActiveState -p NRestarts
```

**3. Repeat crashes rapidly and inspect the refused restart** — VM terminal 1

```bash
for i in $(seq 1 6); do
  sudo systemctl kill --kill-whom=main --signal=KILL ce-lab03-a || true
  sleep 1
done
systemctl show ce-lab03-a -p ActiveState -p Result -p NRestarts
sudo journalctl -u ce-lab03-a -n 15 --no-pager
```

**4. Recover and prove the proxy works again** — VM terminal 1

```bash
sudo systemctl reset-failed ce-lab03-a ce-lab03-b
sudo systemctl start ce-lab03-a ce-lab03-b
systemctl is-active ce-lab03-a ce-lab03-b
# The backends need a moment to bind, and NGINX retries a failed backend after fail_timeout=1s.
for i in $(seq 1 10); do curl -fsS --max-time 3 http://127.0.0.1:8003/ && break; sleep 0.5; done
```

**Recovery check:** Both backends are active and the proxy responds successfully.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

Restart=always requests a restart, but the start-rate limit can refuse it. One crash can remain within the allowance; repeated starts can exhaust it and leave A failed. The journal, not a successful response through B, establishes what happened to A. If the limit was not reached, report that observation rather than claiming it was.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 2:** A should return to active. A successful proxy response alone cannot prove that A restarted.

**Step 3:** Look for "Start request repeated too quickly" and a failed unit. Result and restart counts can vary with timing and systemd version; check the journal.

</details>

<details>
<summary>Optional comparison — beyond the core question</summary>

Optional: disable the start limit on A and repeat. This changes recovery policy, not the reason for the crashes. Run the lab reset afterwards to remove the override.

**1. Optional A/B change, remove the start limit on A, then repeat the A kill loop** — VM terminal 1

```bash
sudo mkdir -p /etc/systemd/system/ce-lab03-a.service.d
printf '[Unit]\nStartLimitIntervalSec=0\n' | sudo tee /etc/systemd/system/ce-lab03-a.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart ce-lab03-a
systemctl show ce-lab03-a -p StartLimitIntervalUSec -p StartLimitBurst
for i in $(seq 1 6); do
  sudo systemctl kill --kill-whom=main --signal=KILL ce-lab03-a || true
  sleep 1
done
systemctl show ce-lab03-a -p ActiveState -p Result -p NRestarts
```

Expected observation: StartLimitIntervalUSec=0. This removes the give-up threshold; it does not fix the crash.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 03 reset`.

<a id="lab-04"></a>

## Lab 04 — CPU contention and a quota

**Question:** How does capping a CPU competitor change the time taken by the same job?

A CPU-bound job needs execution time, but its elapsed time also includes waiting to be scheduled. Two runnable workloads pinned to one CPU compete for that time. A slower iteration can therefore come from contention rather than extra work in the application.

A quota limits the competitor's CPU budget per period. After using its budget, that group is throttled until the next period. A 20% quota means 20 ms per 100 ms, not a reserved core for the other job. Compare job timing with the quota and throttling counters to see whether limiting the neighbour helps.

**Source:** chaos-theory.md: §§3.2, 3.3.5 and the CPU-shares correction; §5.5.2.

**In this lab:** Both workloads use CPU 0. The neighbour runs in ce-lab04 with a finite runtime. Keep the same job and CPU placement in each phase.

**Predict:** Rank the job time with no competitor, an unrestricted competitor and a competitor capped at 20%. Explain your prediction.

1. Run the job three times without the neighbour to establish normal variation.
2. Add the bounded neighbour on CPU 0 and rerun the job; observe CPU waiting.
3. Repeat with CPUQuota=20% on the neighbour; record job time and cpu.stat.
4. Stop the neighbour and rerun the job. Compare the mean times with baseline.

**Explain the result:** Compare the measured job times and quota counters. Explain how throttling the competitor changes waiting for CPU; mark a run inconclusive if the competitor stopped too early.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 04 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Choose an allowed CPU** — VM terminal 1

```bash
cd ~/labs/lab04
taskset -pc $$
# If CPU 0 is not allowed, replace every -c 0 below with one allowed CPU.
```

**2. Record the baseline three times** — VM terminal 1

```bash
cd ~/labs/lab04
for run in 1 2 3; do taskset -c 0 python3 work.py | tee "baseline-$run.txt"; done
sort -k2 -n baseline-*.txt | awk 'NR==1 {min=$2} {max=$2} END {print "iteration range:", min, "-", max, "s"}'
```

**3. Add one bounded CPU neighbour on the same CPU** — VM terminal 1

```bash
cd ~/labs/lab04
sudo systemd-run --unit=ce-lab04 --collect -p RuntimeMaxSec=45s \
  taskset -c 0 stress-ng --cpu 1 --timeout 40s
taskset -c 0 python3 work.py | tee loaded.txt
systemctl is-active --quiet ce-lab04 || echo 'Inconclusive: the neighbour ended before the measurement finished.'
cat /proc/pressure/cpu
vmstat 1 5
sudo systemctl stop ce-lab04
```

**4. Cap the neighbour at 20 percent and read throttling counters** — VM terminal 1

```bash
cd ~/labs/lab04
while systemctl list-units --all --plain --no-legend ce-lab04.service | grep -q .; do sleep 1; done
sudo systemd-run --unit=ce-lab04 --collect -p CPUQuota=20% -p RuntimeMaxSec=45s \
  taskset -c 0 stress-ng --cpu 1 --timeout 40s
taskset -c 0 python3 work.py | tee quota.txt
path=$(systemctl show ce-lab04 -p ControlGroup --value)
if systemctl is-active --quiet ce-lab04 && [ -n "$path" ]; then
  sudo cat "/sys/fs/cgroup$path/cpu.max" "/sys/fs/cgroup$path/cpu.stat"
else
  echo 'Inconclusive: the neighbour ended before the measurement finished.'
fi
sudo systemctl stop ce-lab04
```

**5. Recover and repeat the baseline** — VM terminal 1

```bash
cd ~/labs/lab04
sudo systemctl stop ce-lab04 2>/dev/null || true
while systemctl list-units --all --plain --no-legend ce-lab04.service | grep -q .; do sleep 1; done
taskset -c 0 python3 work.py | tee recovered.txt
for f in baseline-1.txt baseline-2.txt baseline-3.txt loaded.txt quota.txt recovered.txt; do
  awk -v f="$f" '{s+=$2} END {printf "%-15s mean=%.4fs\n", f, s/NR}' "$f"
done
```

**Recovery check:** ce-lab04 is stopped and the final job timing is recorded.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

An unrestricted neighbour competes for CPU time. Capping it should leave more time for work.py, though the measured gain depends on scheduling. cpu.max shows the configured cap; cpu.stat shows throttling. Recovery toward baseline strengthens the contention explanation. A run that outlasts the neighbour mixes contention with recovery and cannot support the comparison.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** The commands below use CPU 0. If CPU 0 is not listed, change every -c 0.

**Step 3:** Compare iteration time with baseline. PSI and vmstat provide supporting waiting measurements; neither alone proves which task caused the slowdown.

**Step 4:** cpu.max should show a quota/period ratio of 0.2, and cpu.stat should show throttling. If the neighbour ends before measurement finishes, shorten work.py's iteration count and repeat every phase with that same workload.

</details>

<details>
<summary>Optional comparison — beyond the core question</summary>

Optional: compare nice 19 with the quota. Nice is a relative scheduling preference, not a CPU ceiling; cgroup scheduling can limit its effect. Run after the core comparison in the same VM shell.

**1. Contrast relative priority (nice) with the hard quota** — VM terminal 1

```bash
cd ~/labs/lab04
while systemctl list-units --all --plain --no-legend ce-lab04.service | grep -q .; do sleep 1; done
sudo systemd-run --unit=ce-lab04 --collect -p RuntimeMaxSec=45s \
  nice -n 19 taskset -c 0 stress-ng --cpu 1 --timeout 40s
taskset -c 0 python3 work.py | tee nice.txt
sudo systemctl stop ce-lab04
awk '{s+=$2} END {printf "nice mean=%.4fs\n", s/NR}' nice.txt
```

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 04 reset`.

<a id="lab-05"></a>

## Lab 05 — A container is several Linux mechanisms

**Question:** Why does an isolated process view not tell you how much CPU a sandbox can use?

chroot changes the root used to resolve filesystem paths. A PID namespace gives processes a separate PID view, and a suitable proc mount lets ps display that view. A mount namespace separates mount configuration. These mechanisms do not themselves limit CPU or memory.

Cgroups separately account for and limit resource use. A sandbox can see only a few processes yet still share the VM's kernel, network and storage. Reading the configured limits and observing a throttled busy loop distinguishes resource enforcement from an isolated-looking view.

**Source:** chaos-theory.md: §§5.2–5.5.2 and §5.7.1.

**In this lab:** The prepared BusyBox sandbox uses chroot, PID and mount namespaces, and a systemd scope with CPU, memory and task limits.

**Predict:** Predict which observation shows a separate PID view and which shows enforced CPU limiting.

1. Start the bounded sandbox and record echo $$, ps and ls / inside it.
2. From the VM, inspect its PID namespace and cpu.max, memory.max and pids.max.
3. Run the busy loop; read cpu.stat twice and observe CPU usage from the VM.
4. Stop the loop and exit. Match the filesystem view, PID view and throttling to their mechanisms.

**Explain the result:** Use the PID view and increasing throttling counters to explain the separate roles of namespaces and cgroups.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 05 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Confirm the exported BusyBox root filesystem** — VM terminal 1

```bash
ls ~/labs/lab05/rootfs
```

**2. Start the sandbox under a resource-limited systemd scope (this shell becomes the sandbox)** — VM terminal 1

```bash
sudo systemd-run --unit=ce-lab05 --scope --collect \
  -p MemoryMax=128M -p MemorySwapMax=0 -p TasksMax=50 -p CPUQuota=20% \
  unshare --fork --pid --mount --mount-proc="$HOME/labs/lab05/rootfs/proc" \
  chroot "$HOME/labs/lab05/rootfs" /bin/sh
```

**3. Inspect the view inside the sandbox** — Sandbox shell (terminal 1)

```bash
echo $$
ps
ls /
```

**4. Read the limits and PID namespaces from the host** — VM terminal 2

```bash
path=$(systemctl show ce-lab05.scope -p ControlGroup --value)
sudo cat "/sys/fs/cgroup$path/cpu.max" "/sys/fs/cgroup$path/memory.max" "/sys/fs/cgroup$path/pids.max"
sudo lsns -t pid
```

**5. Burn CPU inside the sandbox** — Sandbox shell (terminal 1)

```bash
while :; do :; done
```

**6. Observe enforcement from the host while the loop runs** — VM terminal 2

```bash
path=$(systemctl show ce-lab05.scope -p ControlGroup --value)
sudo cat "/sys/fs/cgroup$path/cpu.stat"
sleep 5
sudo cat "/sys/fs/cgroup$path/cpu.stat"
top -b -n 2 -d 2 | awk '/^top -/ {frame++} frame == 2' | head -15
```

**7. Stop the loop with Ctrl-C, then leave the sandbox** — Sandbox shell (terminal 1)

```bash
exit
```

**8. Fallback if the sandbox shell is unresponsive** — VM terminal 2

```bash
sudo systemctl stop ce-lab05.scope
sudo systemctl reset-failed ce-lab05.scope 2>/dev/null || true
```

**Recovery check:** The sandbox is exited and its scope is no longer active.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

The prepared root explains the files under /. The PID namespace explains the different process view. The cgroup explains the CPU cap and throttling. None of these creates a separate kernel or automatically isolates every shared resource.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 3:** $$ is 1, ps lists only the sandbox processes, and / is the BusyBox tree.

**Step 4:** cpu.max 20000 100000, memory.max 134217728, pids.max 50; lsns shows a separate PID namespace whose command is sh.

**Step 6:** nr_throttled and throttled_usec increase; top shows sh near 20 percent CPU.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 05 reset`.

<a id="lab-06"></a>

## Lab 06 — Separate containers can share a full filesystem

**Question:** Why can one container prevent another from writing to a shared filesystem?

Containers can have separate process and filesystem views while still mounting the same underlying storage. A container boundary does not create additional capacity for that shared mount. Both writers consume the same finite pool of free space.

When the shared filesystem is full, a write can fail with No space left on device even in a newly started container. Freeing space and retrying the same write tests whether shared capacity caused the failure. This lab uses a small tmpfs to demonstrate capacity exhaustion; it does not measure physical disk performance.

**Source:** chaos-theory.md: §5.4 and Experiment Card 5.1. The tmpfs fixture adapts the shared-storage example.

**In this lab:** Two disposable containers mount the same 32 MiB tmpfs. Only this small lab mount is filled.

**Predict:** Will a fresh container be able to write after another fills their shared mount?

1. Write one MiB to the empty shared mount to establish the baseline.
2. Fill the mount from one container and repeat the same probe from another.
3. Delete the filling file, repeat the probe and unmount the filesystem.

**Explain the result:** Compare the identical write before filling, while full and after freeing space. Explain which resource the two containers share.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 06 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Mount the small shared filesystem and prove a write works** — VM terminal 1

```bash
mkdir -p ~/labs/lab06/shared
sudo mount -t tmpfs -o size=32m tmpfs "$HOME/labs/lab06/shared"
docker run --rm -v "$HOME/labs/lab06/shared:/data" ubuntu:24.04 sh -c 'dd if=/dev/zero of=/data/probe bs=1M count=1'
sudo rm -f ~/labs/lab06/shared/probe
```

**2. Fill it from one container and repeat the same write from another** — VM terminal 1

```bash
docker run --rm -v "$HOME/labs/lab06/shared:/data" ubuntu:24.04 sh -c 'dd if=/dev/zero of=/data/full bs=1M count=40; df -h /data'
docker run --rm -v "$HOME/labs/lab06/shared:/data" ubuntu:24.04 sh -c 'dd if=/dev/zero of=/data/probe bs=1M count=1'
```

**3. Free the space, repeat the write, and unmount** — VM terminal 1

```bash
sudo rm -f ~/labs/lab06/shared/full ~/labs/lab06/shared/probe
docker run --rm -v "$HOME/labs/lab06/shared:/data" ubuntu:24.04 sh -c 'dd if=/dev/zero of=/data/probe bs=1M count=1'
sudo rm -f ~/labs/lab06/shared/probe
sudo umount ~/labs/lab06/shared
```

**Recovery check:** No ce-lab06 test container remains and the shared tmpfs is unmounted.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

The new container has a separate process environment but uses the same full tmpfs. Its write therefore fails until the filling file is removed. Success before filling and after freeing space supports shared-capacity exhaustion as the explanation. Container separation alone does not protect this shared resource.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** The one-MiB write succeeds before space is consumed.

**Step 2:** The filling write and the second container’s probe reach No space left on device.

**Step 3:** The same probe succeeds after capacity is freed.

</details>

<details>
<summary>Optional comparison — beyond the core question</summary>

Optional: compare CPU, memory and task limits. CPU quotas throttle execution; memory exhaustion may trigger OOM; a task cap refuses new processes. Record the different symptom and evidence in each case. These cgroup limits do not establish separate capacity for a shared filesystem.

**1. Read a hard CPU cap** — VM terminal 1

```bash
source ~/labs/common.sh
docker run -d --name ce-lab06-cpu --cpus=0.5 python:3.12-slim \
  python -c 'import time; end=time.monotonic()+30
while time.monotonic()<end: pass'
path=$(cg ce-lab06-cpu)
cat "$path/cpu.max" "$path/cpu.stat"
docker stats --no-stream ce-lab06-cpu
docker wait ce-lab06-cpu
docker rm ce-lab06-cpu
```

Expected observation: cpu.max shows 50000 100000 and docker stats shows about 50% CPU.

**2. Bound a memory allocator and collect three kinds of evidence** — VM terminal 1

```bash
since=$(date --iso-8601=seconds)
docker run --name ce-lab06-mem --memory=64m --memory-swap=64m python:3.12-slim \
  python -c 'a=[]
while True: a.append(b"x"*1000000)'
echo "exit=$?"
docker inspect ce-lab06-mem --format '{{json .State}}'
sudo journalctl -k --since "$since" --no-pager | grep -iE 'oom|killed process'
docker rm ce-lab06-mem
```

Expected observation: exit=137, "OOMKilled":true and a kernel OOM line naming python.

**3. Bound process creation without a fork bomb** — VM terminal 1

```bash
docker run --name ce-lab06-pids --pids-limit=20 --memory=128m python:3.12-slim python -c '
import subprocess
children=[]
try:
    for i in range(40): children.append(subprocess.Popen(["sleep","15"]))
except OSError as e: print(type(e).__name__,str(e),"children",len(children),flush=True)
finally:
    for p in children: p.terminate()
    for p in children: p.wait()'
docker rm ce-lab06-pids
```

Expected observation: A BlockingIOError (Resource temporarily unavailable) with fewer than 20 children.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 06 reset`.

<a id="lab-07"></a>

## Lab 07 — Tools can act through a shared namespace

**Question:** Why does MySQL’s network delay remain after the helper container exits?

A network namespace contains interfaces, routes and packet-handling settings. A host process or helper container can join MySQL's namespace and configure its interface even though tc is not installed in MySQL's image. The helper needs NET_ADMIN to make that change.

netem adds a queueing rule to the interface. The rule remains after the helper exits because it belongs to the shared network configuration. Delaying MySQL egress delays replies to WordPress; several dependent database exchanges can make a page slower by more than one delay interval.

**Source:** chaos-theory.md: §§5.8–5.8.1 and Experiment Card 5.5.

**In this lab:** The helper joins MySQL’s network namespace and adds 25 ms on eth0 egress. The core uses this method once; the host method is optional.

**Predict:** After the helper exits, predict the qdisc state and the page latency. What action should restore the baseline?

1. Measure the page baseline and check that MySQL has only its default qdisc.
2. Add 25 ms through the helper; after it exits, inspect the qdisc and measure the page.
3. Delete the qdisc and compare the recovered page timing with baseline.

**Explain the result:** Record the qdisc and page timing after the helper exits and after deletion. Explain why removing the injector did not remove its effect.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 07 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Resolve MySQL and measure WordPress** — VM terminal 1

```bash
cd ~/labs/lab07
DB=$(docker compose ps -q db)
PID=$(docker inspect -f '{{.State.Pid}}' "$DB")
dbnet() { [ "$PID" -gt 1 ] || return 1; sudo nsenter --target "$PID" --net -- "$@"; }
dbnet tc qdisc show dev eth0
# Continue only with the default qdisc (noqueue), not an existing custom root qdisc.
source ~/labs/common.sh
measure http://localhost:8080/ 10
```

**2. Add delay from the helper and inspect it after the helper exits** — VM terminal 1, same shell

```bash
docker image inspect ce-tc:lab --format '{{.Config.Entrypoint}}'
docker run --rm --network "container:$DB" --cap-add NET_ADMIN ce-tc:lab qdisc add dev eth0 root netem delay 25ms
docker run --rm --network "container:$DB" --cap-add NET_ADMIN ce-tc:lab -s qdisc show dev eth0
measure http://localhost:8080/ 10
dbnet tc qdisc show dev eth0
docker run --rm --network "container:$DB" --cap-add NET_ADMIN ce-tc:lab qdisc del dev eth0 root
```

**3. Confirm recovery** — VM terminal 1, same shell

```bash
dbnet tc qdisc show dev eth0
measure http://localhost:8080/ 10
```

**Recovery check:** MySQL has no netem qdisc and the page returns toward baseline latency.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

The helper changes the interface’s queueing configuration in MySQL’s network namespace. That configuration outlives the helper process, so its exit does not remove the delay. Deleting the qdisc removes the fault. Page time can increase by more than 25 ms because serving the page can require several database exchanges.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** eth0 shows only the default qdisc (noqueue). Do not continue if a custom root qdisc exists.

**Step 2:** Entrypoint [tc]. The host still sees the netem qdisc after each --rm helper exited: removing the helper does not undo tc.

**Step 3:** eth0 is back to the default qdisc and latency matches the baseline.

</details>

<details>
<summary>Optional comparison — beyond the core question</summary>

Optional: repeat the same 25 ms fault using host tc through nsenter. Use the same shell after core recovery. Both methods change MySQL’s network namespace; compare results and remove the qdisc before resetting.

**1. Add 25 ms on all MySQL egress from the host, measure, recover** — VM terminal 1, same shell

```bash
dbnet tc qdisc add dev eth0 root netem delay 25ms
dbnet tc -s qdisc show dev eth0
measure http://localhost:8080/ 10
dbnet tc qdisc del dev eth0 root
measure http://localhost:8080/ 10
```

Expected observation: Page latency rises by more than 25 ms while the netem counter grows, then returns to baseline.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 07 reset`.

<a id="lab-08"></a>

## Lab 08 — A syscall error tests application handling

**Question:** Why can one request succeed even though its close error stops the server?

A syscall is an application request to the kernel, such as writing bytes or closing a connection. The kernel can return an error, and the application decides how to handle it. A server that normally works may still have a fragile error path.

strace can substitute an EIO error for close in one process. The INJECTED marker identifies the artificial failure. Compare that line with the server's log and process state: a response may already have been sent before close fails. This tests error handling, not throughput; tracing itself adds overhead, and a synthetic error does not reproduce every detail of a real failure.

**Source:** chaos-theory.md: §§6.2–6.4 and Experiment Cards 6.1–6.2.

**In this lab:** Target only the PID saved in server.pid. Use two VM terminals; Ctrl-C in the tracing terminal detaches strace.

**Predict:** Predict the triggering response, process state and next request after close returns EIO.

1. Start the server and request a page; observe its normal syscalls without injecting.
2. Detach the observer, inject EIO into close and request another page.
3. Check the injection marker, server log and process state; try a second request to test whether service continues.
4. Restart without the injector, confirm HTTP works again and stop the recorded server.

**Explain the result:** Connect the injected close error to the server log and exit status. Explain the first and next HTTP results separately.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 08 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Start the compiled book server and record its exact PID** — VM terminal 1

```bash
cd ~/labs/lab08
./legacy_server > ~/labs/lab08-server.log 2>&1 & server=$!
echo "$server" > server.pid
sleep 1
curl -fsS --max-time 3 http://127.0.0.1:8080/ | head -3
echo "server PID=$server"
```

**2. Observe writes, closes and fsyncs without changing behaviour (Ctrl-C to detach)** — VM terminal 2

```bash
PID=$(cat ~/labs/lab08/server.pid)
sudo strace -p "$PID" -e trace=write,close,fsync -o ~/labs/lab08-trace.txt
```

**3. Request one page while the tracer is attached** — VM terminal 1

```bash
curl -sS --max-time 3 -o /dev/null -w '%{http_code} %{size_download}\n' http://127.0.0.1:8080/
```

**4. After Ctrl-C in terminal 2, inspect the trace** — VM terminal 2

```bash
awk -F'(' '{print $1}' ~/labs/lab08-trace.txt | sort | uniq -c
grep -E '= -1' ~/labs/lab08-trace.txt | head
```

**5. Inject EIO into close (leave attached)** — VM terminal 2

```bash
PID=$(cat ~/labs/lab08/server.pid)
sudo strace -p "$PID" -e trace=close -e inject=close:error=EIO
```

**6. Request one page and read the application outcome** — VM terminal 1

```bash
curl -sS --max-time 3 -o /dev/null -w '%{http_code} %{size_download}\n' http://127.0.0.1:8080/
sleep 1
if kill -0 "$server" 2>/dev/null; then echo 'server still running'; else wait "$server"; echo "server exit=$?"; fi
tail -3 ~/labs/lab08-server.log
curl -sS --max-time 3 -o /dev/null -w 'next request: %{http_code}\n' http://127.0.0.1:8080/
```

**7. Restore HTTP service, then stop the test server** — VM terminal 1

```bash
cd ~/labs/lab08
if kill -0 "$server" 2>/dev/null; then kill "$server"; wait "$server"; fi
./legacy_server > ~/labs/lab08-server.log 2>&1 & server=$!
echo "$server" > server.pid
sleep 1
curl -sS --max-time 3 -o /dev/null -w '%{http_code} %{size_download}\n' http://127.0.0.1:8080/
kill "$server"; wait "$server"
rm -f ~/labs/lab08/server.pid
```

**Recovery check:** The server responds after restart, then the test process is stopped.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

This server treats a close error as fatal and should exit with status 1. The triggering request may already have received its response, but a dead process cannot serve later requests. The fault exposes an application error-handling decision, not a Kubernetes or network failure.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** HTML lines from the server. Keep this terminal: wait "$server" only works in it.

**Step 4:** Many write calls, one fsync and one close per request. fsync on a socket returns -1 EINVAL, which is not an outage cause.

**Step 6:** strace shows close(...) = -1 EIO (Input/output error) (INJECTED); the server exits with status 1 after "error closing socket". The next request should fail to connect; record its result separately from the first response.

**Step 7:** HTTP responds after restart; the test server is then stopped.

</details>

<details>
<summary>Optional comparison — beyond the core question</summary>

Optional: alternating write errors and tracer cost. The blocks restart the server, compare untraced and traced controls, inject alternating write errors, then clean up. Header writes and body retries differ; a living process may send invalid HTTP.

**1. Restart the server (detach any tracer first) and confirm the baseline** — VM terminal 1

```bash
cd ~/labs/lab08
./legacy_server > ~/labs/lab08-server.log 2>&1 & server=$!
echo "$server" > server.pid
sleep 1
curl -sS --max-time 3 -o /dev/null -w '%{http_code} %{size_download}\n' http://127.0.0.1:8080/
ab -r -n 200 -c 1 -s 5 http://127.0.0.1:8080/ | grep -E 'Complete requests|Failed requests|Requests per second'
```

**2. Traced, non-injecting control for tracer overhead (Ctrl-C after the next step)** — VM terminal 2

```bash
PID=$(cat ~/labs/lab08/server.pid)
sudo strace -p "$PID" -e trace=write -o /dev/null
```

**3. Measure under the control tracer** — VM terminal 1

```bash
ab -r -n 200 -c 1 -s 5 http://127.0.0.1:8080/ | grep -E 'Complete requests|Failed requests|Requests per second'
```

**4. Inject EIO into the 1st, 3rd, 5th ... write (after Ctrl-C of the control tracer)** — VM terminal 2

```bash
PID=$(cat ~/labs/lab08/server.pid)
sudo strace -p "$PID" -e trace=write -e inject=write:error=EIO:when=1+2
```

**5. Measure status, body completeness and throughput under write injection** — VM terminal 1

```bash
for i in 1 2 3 4 5; do curl -sS --max-time 3 -o /dev/null -w '%{http_code} %{size_download}\n' http://127.0.0.1:8080/; done
ab -r -n 200 -c 1 -s 5 http://127.0.0.1:8080/ | grep -E 'Complete requests|Failed requests|Requests per second'
```

Expected observation: Every request loses its header: curl reports "Received HTTP/0.9 when not allowed" and 000, and strace shows the HTTP/1.0 header write as (INJECTED). The header write in main.c has no retry; respond() retries each failed body write, so body writes succeed. Compare ab's results with the baseline and note the server keeps running.

**6. Recover (Ctrl-C the tracer first)** — VM terminal 1

```bash
kill "$server"; wait "$server"
rm -f ~/labs/lab08/server.pid
```

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 08 reset`.

<a id="lab-09"></a>

## Lab 09 — A syscall denial need not crash the process

**Question:** What changes when the same process installs a filter that denies getpid?

A syscall requests a kernel operation. Seccomp can filter those requests for a process. This program first calls getpid normally, then installs a filter that returns EACCES for getpid while allowing other calls. Comparing the same call before and after installation isolates the filter’s effect.

The denied syscall returns -1 and sets errno; that does not require the application itself to crash. This demonstration prints the result and exits 0 if the denial matched its expectation. The filter applies to the process and is inherited by descendants; it is not installed in the original shell or unrelated processes.

**Source:** chaos-theory.md: §6.5.2; optional capability comparison: §5.8.1.

**In this lab:** Setup compiles filter.c. Run the binary to install the filter only in that test process. The capability comparison is optional.

**Predict:** Predict getpid’s result before and after the filter, and whether the program can still print the error.

1. Run the prepared program and compare getpid before and after filter installation.
2. Record the syscall result, errno and the program’s exit status.
3. Inspect Seccomp in a fresh shell command; distinguish its state from the test process’s filter.

**Explain the result:** Explain the positive PID before filtering, the error afterward and why exit 0 means the demonstration detected the intended denial.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 09 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Run the prepared seccomp demonstration** — VM terminal 1

```bash
cd ~/labs/lab09
./filter; echo "exit=$?"
```

**2. Check an unrelated process after the test exits** — VM terminal 1

```bash
grep Seccomp /proc/self/status
```

**Recovery check:** The demonstration has exited; the filter was scoped to that process. Reset removes the compiled fixture.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

Before the filter, getpid returns the process ID. Afterward, the filter makes it return -1 with errno 13 (EACCES). Printing still works because the filter allows other syscalls. The program’s exit 0 reports a successful check of the denial, not a successful getpid call. Exit 1–3 means filter setup failed; exit 4 means the expected denial was not observed.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** Before filtering, getpid prints a positive PID. After filtering, getpid result=-1 errno=13 and exit=0. Exit 1–3 means filter setup failed; 4 means the expected denial did not occur.

**Step 2:** This fresh process has its own Seccomp state. An existing inherited filter can be present; the test did not install a host-wide policy.

</details>

<details>
<summary>Optional comparison — beyond the core question</summary>

Optional: contrast seccomp with capabilities. SYS_CHROOT authorizes a privileged operation; dropping it can deny chroot even as root. Seccomp instead filters syscall attempts. The comparisons change one control at a time, since an error message alone does not identify the denying layer.

**1. Remove one capability** — VM terminal 1

```bash
docker run --rm ubuntu:24.04 chroot / true; echo "default exit=$?"
docker run --rm --cap-drop SYS_CHROOT ubuntu:24.04 chroot / true; echo "no SYS_CHROOT exit=$?"
docker run --rm --cap-drop ALL ubuntu:24.04 sh -c 'grep CapEff /proc/self/status'
```

Expected observation: The first exits 0; the second prints "chroot: cannot change root directory to '/': Operation not permitted"; CapEff is 0000000000000000.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 09 reset`.

<a id="lab-10"></a>

## Lab 10 — Replacing a Pod is not the same as uninterrupted service

**Question:** What is the difference between replacing a deleted Pod and keeping requests successful?

A Deployment maintains a desired number of replicas through a ReplicaSet. Deleting a managed Pod does not change that desired count, so a new Pod is created and started. It is a replacement object, not the old Pod returning.

A Service provides access while backends change. Remaining replicas may serve during replacement, but readiness and endpoint updates are asynchronous. Running does not mean Ready, and a TCP readiness check does not prove every HTTP request succeeds. Observe the replacement and the client responses separately.

**Source:** chaos-theory.md: §10.4, Experiment Card 10.1 and §§12.1.1–12.1.4.

**In this lab:** The chaos cluster has three Goldpinger replicas. The readiness probe checks TCP 8080; HTTP probes sample /healthz through the Service.

**Predict:** Predict the replacement’s identity and the number of failed probes; explain why these are separate observations.

1. Confirm three Ready replicas and a working HTTP baseline; save the Pod names.
2. Start the 100 HTTP probes, then delete exactly one managed Pod.
3. Wait for three Ready replicas and inspect the replacement and endpoints.
4. Count non-200 probes and explain whether service continued during replacement.

**Explain the result:** Report the replacement identity and non-200 count out of 100 probes. Explain what each observation establishes and why zero sampled failures cannot prove uninterrupted service.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 10 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Checkpoint the prepared chaos cluster** — VM terminal 1

```bash
source ~/labs/common.sh
k get nodes
k get pods -l app=goldpinger -o wide
k auth can-i list pods --as=system:serviceaccount:chaos-labs:goldpinger
k auth can-i delete pods --as=system:serviceaccount:chaos-labs:goldpinger
NODE_IP=$(docker inspect -f '{{.NetworkSettings.Networks.kind.IPAddress}}' chaos-control-plane)
curl -fsS --max-time 3 "http://$NODE_IP:30080/healthz"; echo
k get endpointslices -l kubernetes.io/service-name=goldpinger -o wide
```

**2. Start 100 probes about 0.2 s apart (start this right before the deletion)** — VM terminal 2

```bash
source ~/labs/common.sh
NODE_IP=$(docker inspect -f '{{.NetworkSettings.Networks.kind.IPAddress}}' chaos-control-plane)
for i in $(seq 1 100); do
  code=$(curl -s --max-time 1 -o /dev/null -w '%{http_code}' "http://$NODE_IP:30080/healthz")
  printf '%s %s\n' "$(date --iso-8601=ns)" "$code"
  sleep 0.2
done | tee ~/labs/lab10/probes.log
```

**3. Delete exactly one managed pod and watch the replacement (Ctrl-C once three pods are 1/1 Ready)** — VM terminal 1, same shell

```bash
k get pods -l app=goldpinger -o wide
victim=$(k get pods -l app=goldpinger -o jsonpath='{.items[0].metadata.name}')
echo "victim=$victim deleted_at=$(date --iso-8601=ns)"
k delete pod "$victim" --wait=false
k get pods -l app=goldpinger --request-timeout=0 -w
```

**4. After all 100 probes finish in terminal 2, collect recovery evidence** — VM terminal 1, same shell

```bash
k rollout status deployment/goldpinger --request-timeout=0 --timeout=180s
k get pods -l app=goldpinger -o custom-columns='NAME:.metadata.name,READY:.status.conditions[?(@.type=="Ready")].status,START:.status.startTime,NODE:.spec.nodeName'
k get pod "$victim" 2>&1 | tail -1
k get endpointslices -l kubernetes.io/service-name=goldpinger -o wide
samples=$(wc -l < ~/labs/lab10/probes.log)
if [ "$samples" -eq 100 ]; then
  echo "non-200 samples: $(grep -vc ' 200$' ~/labs/lab10/probes.log)"
  grep -v ' 200$' ~/labs/lab10/probes.log | head
else
  echo "Only $samples/100 samples recorded; wait for terminal 2 to finish before counting."
fi
```

**Recovery check:** Three replicas are Ready and the Service responds.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

The ReplicaSet creates a replacement because the desired replica count remains three. Remaining backends may serve requests during that work, but endpoint changes and in-flight requests can still produce failures. A replacement proves reconciliation; the probe results measure sampled service availability. Zero failed samples means no failure was observed by these probes, not that every possible request succeeded.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** Three Ready replicas, matching endpoints and a working /healthz probe. The workload may list Pods but may not delete them.

**Step 4:** The victim is NotFound, a new pod name replaced it, all READY=True, three endpoints and a counted number of non-200 samples (0 or a few, right after the deletion).

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 10 reset`.

<a id="lab-11"></a>

## Lab 11 — Health depends on what you test

**Question:** Why can the same Pod be Ready while peers report it as unhealthy?

A timeout is the caller’s waiting budget. A running server can respond too late for a caller and still remain alive. If injected latency exceeds the ping budget, peer requests can time out without the target process stopping.

Readiness is only as informative as its configured probe. Here Kubernetes checks whether it can establish a TCP connection to the proxy; peer pings need an application response within 300 ms. The connection can succeed while the response arrives too late. Comparing the two checks exposes different definitions of health.

**Source:** chaos-theory.md: §10.4.4 and Experiment Card 10.2. The timeout and readiness criteria are specific to this fixture.

**In this lab:** The extra Goldpinger replica receives traffic through Toxiproxy. Peer pings use 300 ms; readiness checks the proxy’s TCP listener.

**Predict:** With a 400 ms delay and a 300 ms ping budget, predict the peer result and TCP readiness result separately.

1. Create the proxy listener and confirm healthy peer pings and Pod readiness.
2. Add 400 ms latency; compare fresh peer reports with the Pod’s Ready state.
3. Remove the delay, confirm pings recover, then delete the extra Pod and stop the port-forward.

**Explain the result:** Compare peer pings and readiness before, during and after delay. Explain the different operation each check measures.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 11 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Connect the prepared proxy and establish the no-delay baseline** — VM terminal 1

```bash
source ~/labs/lab10/connect-proxy.sh
pings
k get pod goldpinger-slow
```

**2. Add 400 ms and compare peer pings with readiness** — VM terminal 1

```bash
curl -fsS --max-time 5 -H 'Content-Type: application/json' -X POST "$T/proxies/slow/toxics" -d '{"name":"lat","type":"latency","stream":"upstream","toxicity":1,"attributes":{"latency":400,"jitter":0}}'
sleep 8
pings
k get pod goldpinger-slow
```

**3. Remove the fault, verify recovery, delete the pod and stop the port-forward** — VM terminal 1, same shell

```bash
curl -fsS -X DELETE "$T/proxies/slow/toxics/lat"
curl -fsS "$T/proxies/slow/toxics"; echo
sleep 8
pings
k delete pod goldpinger-slow --wait=true
kill "$(cat ~/labs/lab10/lab11-port-forward.pid)"; rm -f ~/labs/lab10/lab11-port-forward.pid
k rollout status deployment/goldpinger --request-timeout=0 --timeout=180s
k get pods -l app=goldpinger
```

**Recovery check:** The toxic is removed and the original three replicas are Ready.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

At 400 ms of added latency, a peer with a 300 ms budget should report failure. TCP readiness can remain successful because establishing the connection does not require the delayed application response. Removing the delay should restore peer success without restarting the Pod. If the baseline or recovery fails, resolve that before attributing the disagreement solely to the dose.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** The extra replica is Ready and peer reports for its IP show OK true. Establish this baseline before adding delay.

**Step 2:** Look for failed peer pings while the Pod remains Ready. The 400 ms delay exceeds the 300 ms ping budget; readiness only checks TCP connection establishment.

**Step 3:** No toxic remains, peer pings recover, and the original three replicas are Ready after the extra Pod is deleted.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 11 reset`.

<a id="lab-12"></a>

## Lab 12 — Test whether the checker detects failure

**Question:** How do you show that a startup checker detects a missed deadline and subsequent recovery?

Startup is useful only when the requested workload can serve. Timing an HTTP response through its Service includes more of that path than checking whether the Pod is Running. The result is one service-level measurement, not proof of long-term reliability.

A checker that only sees healthy runs might be wrong. Introduce a known delay beyond its 30-second budget, then restore the healthy version. Deleting the previous workload prevents it from answering for the next test. The last-run timestamp distinguishes a recent result from one left by a stopped checker.

**Source:** chaos-theory.md: §11.2 and Experiment Card 11.2.

**In this lab:** Setup prepares the checker and manifest. Each invocation creates a fresh workload, waits up to its 30-second budget, records a result and cleans up. The image is preloaded.

**Predict:** Predict success and elapsed time for normal startup, a 45-second delay, and the restored workload.

1. Run one healthy trial; record HTTP startup time and the checker’s exit status.
2. Add the 45-second startup delay and repeat against the same 30-second budget.
3. Restore the manifest and repeat once more; confirm the test objects are removed.

**Explain the result:** Give the three results and explain why an HTTP deadline miss differs from a checker that exits without recording a trial.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 12 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Run one healthy check and confirm cleanup** — VM terminal 1

```bash
cd ~/labs/lab12
source ~/labs/common.sh
bash run.sh | tee runs.txt
echo "checker exit=${PIPESTATUS[0]} (0 means the loop completed)"
cat metrics/start.prom
k get pod startup-check; k get svc startup-check
```

**2. Prove the check detects a deliberately delayed startup** — VM terminal 1

```bash
cd ~/labs/lab12
cp startup-delayed.yaml startup.yaml
grep -n 'command:' startup.yaml
bash run.sh | tee runs-delayed.txt
echo "checker exit=${PIPESTATUS[0]} (0 means the loop completed)"
```

**3. Restore the healthy command and repeat the check** — VM terminal 1

```bash
cd ~/labs/lab12
cp startup-good.yaml startup.yaml
grep -n 'command:' startup.yaml
bash run.sh | tee runs-restored.txt
echo "checker exit=${PIPESTATUS[0]} (0 means the loop completed)"
```

**4. Manual fallback if the loop was killed** — VM terminal 2

```bash
source ~/labs/common.sh
k delete -f ~/labs/lab12/startup.yaml --ignore-not-found --grace-period=1
```

**Recovery check:** The healthy manifest is restored and no startup-check Pod or Service remains.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

The delayed workload should miss the 30-second budget and be reported as unsuccessful. Restored healthy runs check that the fault was removed. These trials validate those checker paths; they do not establish an SLO for all future startups.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** One result with success=1 and a few seconds elapsed; both final gets report NotFound. A nonzero checker exit or no new result means the check did not complete; do not interpret old metrics as a new result.

**Step 2:** The grep shows the sleep 45 command; the run reports success=0 after about 30 s.

</details>

<details>
<summary>Optional comparison — beyond the core question</summary>

Optional: run five healthy cycles to observe variation, then interrupt another run with Ctrl-C. Verify that its Pod and Service are removed. The saved metric is the last completed trial; its timestamp must advance before it can represent a new result.

**1. Repeat healthy checks** — VM terminal 1

```bash
cd ~/labs/lab12
bash run.sh 5 | tee runs-repeated.txt
echo "checker exit=${PIPESTATUS[0]}"
cat metrics/start.prom
```

**2. Start another run, press Ctrl-C, then inspect cleanup** — VM terminal 1

```bash
cd ~/labs/lab12
bash run.sh
# Press Ctrl-C while the script is running; after it exits:
source ~/labs/common.sh
k get pod startup-check; k get svc startup-check
cat metrics/start.prom
```

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 12 reset`.

<a id="lab-13"></a>

## Lab 13 — Losing supervision does not stop the process

**Question:** Why can Kubernetes replace a Pod while its original container is still running?

Kubelet supervises assigned containers and reports node status. The container runtime is separate, so stopping kubelet does not inherently stop existing application processes. It does stop the normal reporting and reconciliation path.

The control plane first detects missing reports, then waits through applicable eviction tolerations before replacing the workload. Scheduling and startup take more time. Meanwhile, an API object being deleted does not prove its process stopped on the disconnected node. Inspect the runtime as well as the Pod list.

**Source:** chaos-theory.md: §§12.1.1–12.1.3 (kubelet experiment ideas).

**In this lab:** Stop only kubelet in the node actually hosting node-web. Read the Pod's tolerations; observe for at most eight minutes, then restore kubelet.

**Predict:** Predict whether stopping kubelet immediately stops the container, and whether detection and replacement occur together.

1. Record the actual node, Pod identity and tolerations; start timestamped node and Pod watches.
2. Stop kubelet on that node and check the original container with crictl.
3. Observe detection and replacement, checking runtime state too; stop waiting after eight minutes.
4. Restart kubelet and confirm four Ready nodes and one Ready node-web Pod.

**Explain the result:** Compare the node/Pod timeline with crictl on the original node. Explain why control-plane replacement does not establish that the old process stopped.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 13 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Find the worker running node-web and inspect its tolerations** — VM terminal 1

```bash
source ~/labs/common.sh
k rollout status deployment/node-web --request-timeout=0 --timeout=180s
k get pods -l app=node-web -o wide
NODE=$(k get pods -l app=node-web -o jsonpath='{.items[0].spec.nodeName}')
echo "NODE=$NODE"
k get pods -l app=node-web -o jsonpath='{.items[0].spec.tolerations}'; echo
```

**2. Timestamped node watch** — VM terminal 2

```bash
source ~/labs/common.sh
k get nodes --request-timeout=0 -w | while IFS= read -r line; do printf '%s %s\n' "$(date +%T)" "$line"; done
```

**3. Timestamped pod watch** — VM terminal 3

```bash
source ~/labs/common.sh
k get pods -l app=node-web -o wide --request-timeout=0 -w | while IFS= read -r line; do printf '%s %s\n' "$(date +%T)" "$line"; done
```

**4. Stop only kubelet on that worker** — VM terminal 1, same shell

```bash
date --iso-8601=seconds
docker exec "$NODE" systemctl stop kubelet
docker exec "$NODE" crictl ps --name web
```

**5. Sample detection, taints and eviction (repeat every minute; stop after eight minutes without a replacement)** — VM terminal 1, same shell

```bash
date --iso-8601=seconds
k get node "$NODE"
k get node "$NODE" -o jsonpath='{.spec.taints}'; echo
k get pods -l app=node-web -o wide
docker exec "$NODE" crictl ps --name web
```

**6. Restore kubelet before any other fault** — VM terminal 1, same shell

```bash
docker exec "$NODE" systemctl start kubelet
k wait --for=condition=Ready "node/$NODE" --request-timeout=0 --timeout=180s
k rollout status deployment/node-web --request-timeout=0 --timeout=180s
k get nodes
k get pods -l app=node-web -o wide
```

**Recovery check:** Kubelet is running, four nodes are Ready and one node-web Pod is Ready.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

Missing kubelet reports trigger detection and eviction, not an immediate process kill. Replacement includes several waits, while the old runtime may keep serving its container. Restoring kubelet allows that node to reconcile and clean up.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** The pod is Ready on chaos-worker (the affinity is only preferred, so it can land on another worker; every later command uses $NODE). The not-ready and unreachable NoExecute tolerations have tolerationSeconds 300.

**Step 4:** The web container is still Running although kubelet stopped.

**Step 5:** After the node-monitor grace period (50 s on Kubernetes v1.37) the node turns NotReady with node.kubernetes.io/unreachable taints. About 300 s after that the old pod goes Terminating and a replacement starts on another worker, while crictl still shows the old container running.

**Step 6:** All four nodes Ready and one Ready node-web pod on another worker. The old pod can still show Terminating for up to a minute while the restored kubelet stops its container. Stop the watches with Ctrl-C.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 13 reset`.

<a id="lab-14"></a>

## Lab 14 — Quorum controls writes, not every application request

**Question:** Why can existing HTTP traffic work when etcd cannot commit API writes?

etcd needs a majority of voting members to commit a change. Three members need two: losing one leaves a majority; losing two does not. This protects agreement on stored state instead of allowing a minority to accept conflicting changes.

Kubernetes API writes depend on etcd, but existing application traffic can use already-running containers and installed network rules. Compare a ConfigMap write with an HTTP request to distinguish management availability from application availability. A successful cached read alone does not demonstrate that a new change can commit.

**Source:** chaos-theory.md: §12.1.1 (etcd and Raft) and §12.1.4 (Service routing).

**In this lab:** Use the separate ha cluster. Move static etcd manifests to stop members and restore the same manifests to recover them; Docker provides a fallback independent of kubectl.

**Predict:** Predict write and HTTP results after losing one of three members, then two.

1. Confirm three etcd members, a successful ConfigMap write and a working HTTP baseline.
2. Stop one member, wait 30 seconds and probe both paths.
3. Stop a second member, wait 30 seconds and repeat the bounded probes.
4. Restore both manifests; confirm healthy endpoints, a successful write and HTTP recovery. Use the Docker fallback if API access fails.

**Explain the result:** Report write and HTTP results at each phase. Use the two-member majority and the existing traffic path to explain any difference.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 14 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Establish HTTP and write baselines** — VM terminal 1

```bash
source ~/labs/lab14/helpers.sh
h get nodes
h rollout status deployment/quorum-web --request-timeout=0 --timeout=180s
PORT=$(h get svc quorum-web -o jsonpath='{.spec.ports[0].nodePort}')
IP=$(docker inspect -f '{{.NetworkSettings.Networks.kind.IPAddress}}' ha-worker)
curl -fsS --max-time 3 "http://$IP:$PORT/" >/dev/null && echo 'HTTP baseline ok'
h patch configmap quorum-probe --type merge -p '{"data":{"state":"baseline"}}'
ec ha-control-plane endpoint status --cluster -w table
```

**2. Stop one etcd member and probe both paths** — VM terminal 1, same shell

```bash
stop_etcd ha-control-plane2
sleep 30
docker exec ha-control-plane2 crictl ps --name etcd
h patch configmap quorum-probe --type merge -p '{"data":{"state":"one-down"}}'
curl -sS --max-time 3 -o /dev/null -w '%{http_code}\n' "http://$IP:$PORT/"
```

**3. Stop a second member, probe, then restore both** — VM terminal 1, same shell

```bash
stop_etcd ha-control-plane3
sleep 30
h patch configmap quorum-probe --type merge -p '{"data":{"state":"two-down"}}'
curl -sS --max-time 3 -o /dev/null -w '%{http_code}\n' "http://$IP:$PORT/"
start_etcd ha-control-plane2
start_etcd ha-control-plane3
sleep 30
for _ in $(seq 1 12); do ec ha-control-plane endpoint health --cluster && break; sleep 5; done
# The API servers need a few seconds after etcd heals: expect a timeout or Forbidden before the write succeeds.
for _ in $(seq 1 24); do h patch configmap quorum-probe --type merge -p '{"data":{"state":"recovered"}}' && break; sleep 5; done
for _ in $(seq 1 12); do h get configmap quorum-probe -o jsonpath='{.data.state}' && break; sleep 5; done; echo
curl -fsS --max-time 3 "http://$IP:$PORT/" >/dev/null && echo 'HTTP recovery ok'
```

**4. Independent fallback that restores the manifests without kubectl** — VM terminal 2

```bash
for node in ha-control-plane2 ha-control-plane3; do
  docker exec "$node" sh -c 'test -f /root/ce-etcd.yaml && mv /root/ce-etcd.yaml /etc/kubernetes/manifests/etcd.yaml; ls /etc/kubernetes/manifests'
done
```

**Recovery check:** Three etcd endpoints are healthy and both write and HTTP probes succeed.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

Two surviving members can commit; one cannot. Existing HTTP traffic may continue because it does not need a new etcd write for each request. Brief transition errors are possible even with quorum. Restoring these members tests temporary quorum recovery, not recovery from permanent data loss.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** Four Ready nodes, 2/2 web pods, HTTP ok, "configmap/quorum-probe patched" and a table with three members, one IS LEADER=true.

**Step 2:** No etcd container on ha-control-plane2; the write normally succeeds because two of three members keep quorum (a single failure can come from the stopped member's API server before the load balancer drops it, so retry once); HTTP returns 200.

**Step 3:** Without a majority, writes should fail while the established HTTP path may continue. After restoration, wait for endpoint health and a successful recovered write; record any transition failures.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 14 reset`.

<a id="lab-15"></a>

## Lab 15 — Retries can multiply work

**Question:** How do retries change backend work per original request during the same slowdown?

One user request can cause several attempts. If the client retries and NGINX retries each client attempt, their limits multiply: two attempts at each layer allow up to four backend arrivals. Actual amplification depends on which attempts fail or succeed.

A caller timing out does not necessarily cancel work already running downstream. Slow requests hold worker slots while retries add more work. Retrying may recover an operation or worsen contention. Compare backend arrivals per original request with successful user outcomes, using the same load and slowdown in both runs.

**Source:** chaos-theory.md: §1.2.3 (retry amplification) and §1.5 (dependency failures).

**In this lab:** Each case starts fresh upstreams and runs 80 requests. Five seconds after load starts, response delay rises from 0.2 to 1 second for five seconds. NGINX permits two upstream attempts per client attempt with a 0.5-second read timeout. Only the client retry setting changes. The runner prints measurements and cleans up its processes.

**Predict:** Predict backend arrivals per request and user successes with one client retry versus none.

1. Run the prepared case with one client retry; record amplification and successes out of 80.
2. Run it again with zero client retries and compare the same measurements.
3. Confirm normal delay and remove the proxy configuration. Explain the extra work without assuming retries must improve success.

**Explain the result:** Compare arrivals / 80 and successful requests / 80 for both settings. Explain why the retry limits bound attempts but do not guarantee a particular success rate.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 15 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Run with one client retry** — VM terminal 1

```bash
cd ~/labs/lab15
bash run-case.sh 1
```

**2. Repeat with no client retry** — VM terminal 1

```bash
cd ~/labs/lab15
bash run-case.sh 0
```

**3. Confirm the delay is normal and remove the lab proxy** — VM terminal 1

```bash
cd ~/labs/lab15
cat delay.txt
sudo rm -f /etc/nginx/conf.d/ce-lab15.conf
sudo nginx -t && sudo systemctl reload nginx
```

**Recovery check:** Normal delay is restored, upstream processes are stopped and the lab proxy config is removed.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

Removing client retries removes one source of extra work; proxy retries can still amplify requests. Compare both runs using arrivals per original request and successes out of 80. The retry limits give an upper bound, not a guaranteed multiplier. Continued failures after the delay ends can indicate backlog; this short run alone does not prove a self-sustaining failure.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 1:** The runner checks the baseline, runs 80 original requests with the timed slowdown, prints arrivals and successes, then stops its upstreams.

**Step 2:** Compare amplification and successes with the first run. Proxy retries remain enabled, so zero client retries does not imply one backend arrival per original request.

**Step 3:** delay.txt is 0.2. Each completed runner stops its own upstreams; the proxy configuration is now removed.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 15 reset`.

<a id="lab-16"></a>

## Lab 16 — Design one clear experiment

**Question:** How would you test one resilience claim so the result has a clear meaning?

A useful chaos experiment starts with a measurable service outcome. Its hypothesis states what should happen when one defined fault occurs. A baseline tells you how the service behaves without that fault, so the comparison has meaning.

Choose an exact target and a finite duration. Define when to stop, how to remove the fault and how to confirm service recovery. The removal path must remain available if the injector fails. This exercise is a design on paper: a completed card is a plan, not evidence that the system passed.

**Source:** chaos-theory.md: §§1.3, 2.5; Appendix C; Master Cheat Sheet §6.

**In this lab:** Fill the prepared card for one service and one fault. Nothing is deployed or disrupted in this lab.

**Predict:** State what you expect to measure under one fault and why the service should behave that way.

1. Choose one service outcome and write its normal baseline.
2. Choose one bounded fault and state the expected outcome in measurable terms.
3. Write the stop condition, rollback and recovery check, including a fallback if the normal removal path fails.
4. Read the card as another operator: can you run and stop the test without guessing?

**Explain the result:** Write a card another person can follow: measurable baseline, one fault, expected result, stop condition, rollback and recovery evidence. Keep it a plan; do not invent observations.

<details>
<summary>Core procedure — run after predicting</summary>

Run `./ansible/run-lab.sh 16 setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.

**1. Fill the short experiment card** — VM terminal 1

```bash
cd ~/labs/lab16
${EDITOR:-nano} experiment-card.md
```

**2. Find unanswered fields** — VM terminal 1

```bash
cd ~/labs/lab16
grep -nE ':[[:space:]]*$' experiment-card.md
check_status=$?
case "$check_status" in
  0) echo 'Fill the fields listed above.' ;;
  1) echo 'No blank fields found; review the answers for clarity.' ;;
  *) echo 'Could not read the card; fix the file error before continuing.' >&2 ;;
esac
```

**Recovery check:** The card answers each field clearly; this is a design review, not a live test.

</details>

<details>
<summary>Solution — compare after explaining your result</summary>

A complete experiment connects one controlled fault to one measurable outcome. It also states how to stop and restore the service. If the outcome cannot be measured or the fault cannot be removed, improve the design before considering a run.

Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.

**Step 2:** No blank fields remain. Read the answers too: this check does not validate their meaning.

</details>

<details>
<summary>Optional comparison — beyond the core question</summary>

Optional: review automation failures and staged rollout. Complete the extra questions only when turning the paper experiment into an operational check.

**1. Record the review of the experiment's own failure modes** — VM terminal 1

```bash
cd ~/labs/lab16
cat >> experiment-card.md <<'MARKDOWN'

## Failure review of the experiment itself
Selector matches zero objects:
Selector matches far more objects than expected:
Injector dies mid-run (how is the active fault removed?):
API unavailable during rollback (independent fallback):
Results stop arriving (missing-results alert):
Staged plan (no-fault control, supervised disposable run, approved pilot):
MARKDOWN
${EDITOR:-nano} experiment-card.md
grep -nE ':[[:space:]]*$' experiment-card.md
check_status=$?
case "$check_status" in
  0) echo 'Fill the fields listed above.' ;;
  1) echo 'No blank fields found; review the answers for clarity.' ;;
  *) echo 'Could not read the card; fix the file error before continuing.' >&2 ;;
esac
```

Expected observation: A reviewer can name the target, expected result, stop command and recovery probe without asking the author.

</details>

After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh 16 reset`.

## Source and verification

Edit `ansible/labs/*.yml`, then regenerate this guide with `python3 scripts/render-labs.py`. The terminal cards use those same definitions. `chaos-theory.md` remains the detailed reference; source citations use the original section numbers retained in that file rather than its renumbered chapter headings.

Local validation checks document consistency, rendering and command syntax. It does not establish live Ubuntu, Docker or Kubernetes outcomes. A successful experiment supports only the conditions and measurements actually tested.
