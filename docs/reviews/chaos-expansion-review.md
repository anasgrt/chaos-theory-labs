# Container and Kubernetes chaos expansion review

> Historical review: this report describes an earlier revision. The current catalog
> contains 27 container and Kubernetes labs, renumbered 00 through 26. Lab numbers
> and counts below use the original catalog and are historical evidence, not current
> setup instructions. See [the numbering map](../lab-numbering.md) for retained labs.

Reviewed 20 September 2026. This records the design, checks and validation limits
for four labs added after the troubleshooting expansion: Labs 22–25. Existing lab
numbers, procedures and theory sections are unchanged.

## Why these four

The earlier labs covered container signals and storage, scheduling and runtime
resources, Service connectivity, configuration and rollouts, node and etcd
failure. Four mechanisms that cause frequent production incidents had no lab:
process-table exhaustion inside a container, the drain race during ordinary Pod
deletion, the cost and dependency shape of cluster DNS, and admission control as
a synchronous dependency of the API server.

## Alignment

| Lab | Main theory | Question-card preparation | Required comparison |
| --- | --- | --- | --- |
| 22 | §§5.14.1–5.14.2 | PID namespaces, orphan re-parenting, `wait`, zombie state, `pids.current`/`pids.max`, `EAGAIN` | No init versus explicit reaper for the same 40 orphans; bursts of 40 and 200 against one 64-PID budget |
| 23 | §§10.9.1–10.9.2 | Parallel deletion sequences, EndpointSlice `ready`/`serving`/`terminating`, `preStop`, one grace budget | No hook; `preStop` 5 s with a 30 s budget; the same hook with a 2 s budget |
| 24 | §§10.10.1–10.10.2 | `resolv.conf`, `ndots`, search-list arithmetic, trailing dot, CoreDNS request counter | In-cluster short and absolute names; external name at `ndots` 5, as an FQDN and at `ndots` 1; an absent name; CoreDNS removed |
| 25 | §§12.4.1–12.4.2 | Admission position in the request path, `failurePolicy`, `timeoutSeconds`, selectors, controller events | Backend available; backend removed under `Fail`; controller-driven and unscoped creation; `Ignore`; restored |

Each card teaches its mechanism before any command, states the fixture's actual
numbers, explains every measurement including failure evidence, and asks for a
prediction, recorded observations and a transfer answer. Solutions stay separate
and describe expected patterns rather than measurements.

## Isolation

Lab 22 is a Docker lab: it owns only `ce-lab22-*` containers and removes them in
its procedure and in reset. Labs 23–25 declare `kubernetes: true` and use their
own kind clusters `lab23`, `lab24` and `lab25`, their own kubeconfigs and the
namespaces `ce-lab23`, `ce-lab24`, `ce-lab25` and `ce-lab25-system`. Central
cleanup deletes only the selected cluster and workspace.

Two labs change objects outside their own namespace, inside their own cluster
only. Lab 24 scales the `coredns` Deployment in `kube-system` after saving its
original replica count and restores it in the procedure. Lab 25 installs a
cluster-scoped `ValidatingWebhookConfiguration` whose `namespaceSelector` matches
only `ce-lab25`, so admission for the rest of that cluster, including the
webhook's own namespace, is never intercepted. Both are removed with the cluster.

## Automated and document checks

- 26 definitions, 52 question/solution cards and 227 shell blocks passed the
  content, theory-mapping, rendering and syntax checks in `scripts/check-labs.py`.
- All 36 Kubernetes resources in `labs/*/files/` — existing and new — validated
  against the strict standalone Kubernetes 1.32 JSON schemas.
- `tests/test-lifecycle.sh` passed after extending its lab loop to 00–25 and
  moving its rejected-ID probe to 26.
- `tests/test_repository_layout.py` and `tests/test_labs.py` passed, so all 52
  Ansible-rendered cards match the offline renderer and every new fixture
  installs from its own lab directory.
- `ansible/provision.yml`, `ansible/labs.yml` and `ansible/cards.yml` passed
  syntax checks. The reset integration playbook now also covers clusters
  `lab23`, `lab24` and `lab25`.
- The learner guide `docs/chaos-labs.md` was regenerated and matches the definitions.
- The complete gate, `bash scripts/validate.sh`, passed in a Debian Linux
  container: content checks, lifecycle routing, all three playbook syntax checks,
  the identity rejection playbook and all 34 regression tests, including the
  `/proc` process-identity checks and the reset integration with clusters
  `lab23`, `lab24` and `lab25`.

## Live results

All four labs were executed on a macOS review host: Docker 29.8 with cgroup v2,
and kind v0.33.0 clusters running Kubernetes v1.37.0 on ARM64, using the
repository's own four-node `kind.yaml`. Each Kubernetes lab ran its real setup,
verify, full procedure and verify again, in its own cluster named `lab23`,
`lab24` and `lab25`. This was not the Vagrant VM and not AMD64.

- **22.** Re-run after the PID 1 application was inlined. No-init container: 40 zombies with `ppid=1`, `pids.current=42`, and a
  burst of 40 created 22 processes before `errno=11 Resource temporarily
  unavailable` at `pids.current=pids.max=64`. Reaper container: `reaped pid=`
  lines, zero zombies, `pids.current=2`, all 40 created in the next burst, and
  the ceiling reached only at 62 of 200 requested. Host process count unchanged.
- **23.** Four deletions under 25 requests per second, ~328 requests each:

  | Case | In-flight at SIGTERM | SIGTERM after deletion | Failed requests |
  | --- | --- | --- | --- |
  | Graceful, no hook | 17 / 19 | +0.5 s | 1 / 0 |
  | Abrupt, no hook | 29 / 15 | +0.1 s | 29 / 15 |
  | Abrupt, `preStop sleep 5` | 0 / 0 | +5.3 s | 0 / 0 |
  | Same hook, 1 s budget | 9 / 13 | +1.7 s | 9 / 13 |

  Two runs are shown, the second on the unified manifests. The failure count
  equalled the in-flight count in every abrupt case.

  Baseline and restored probes recorded 140 of 140 successful requests. The
  sampled EndpointSlice conditions showed `ready:false, serving:true,
  terminating:true` for the deleted address in every case.
- **24.** Both clients listed the same three search entries, with `ndots:5` and
  `ndots:1`. The short Service name and its absolute form cost 2 queries each;
  `dl.k8s.io` cost 8 at `ndots:5`, 2 with a trailing dot and 2 from the `ndots:1`
  client — a factor of 4 from a 3-entry search list. The absent name cost 8 from
  *both* clients, confirming that `ndots` reorders candidates without reducing
  them for a failed lookup. With CoreDNS at zero replicas, lookups failed while
  HTTP to the ClusterIP returned 200 and `kubectl` kept working; the counter read
  `unavailable`. After restoring 2 replicas the short name returned to 2 queries.
- **25.** The self-signed certificate and `caBundle` were accepted by the API
  server. Baseline: labelled Pod admitted, unlabelled Pod denied with the policy
  message, one review logged per request. With the backend at zero replicas, a
  labelled Pod create failed in 0.07 s with `failed calling webhook ... connect:
  connection refused`; the Deployment was accepted but its ReplicaSet reported
  `ReplicaFailure` and `FailedCreate` with zero replicas, while a Pod in the
  unscoped namespace was created normally. Under `Ignore`, the Pod the policy
  forbids was created. After recovery the Deployment converged, a labelled Pod
  was admitted and a server-side dry run of the unlabelled Pod was denied again.
- **Reset.** `kind delete cluster` removed each lab's four nodes cleanly, and no
  `ce-lab*` containers or clusters remained afterwards.

## Defects found by these runs, and fixed

1. **Lab 23 did not demonstrate its own question.** With a server that finishes
   in-flight requests, the deletion produced 0–1 failures out of 330: the
   application absorbed the race. The lab now runs the same server in a
   `graceful` and an `abrupt` mode and compares four cases, so the overlap and
   its consequence are separated. Failures now equal the in-flight count.
2. **A theory claim was wrong.** A `preStop` hook longer than the grace budget
   does not produce SIGKILL. The kubelet ends the hook at the deadline and sends
   SIGTERM then: measured at +1.7 s with a 1-second budget against +5.3 s with a
   30-second budget. §10.9.2 and the card were rewritten around the measurement.
3. **The abrupt mode was a silent no-op.** Restoring `SIG_DFL` and re-raising
   SIGTERM does nothing, because the container's main process is PID 1 and the
   kernel discards a signal whose disposition is the default. The fixture now
   exits explicitly with 143, and the card teaches that PID 1 rule.
4. **Rollout traffic was counted as failures.** Probes started while the previous
   rollout's old Pods were still terminating, adding failures unrelated to the
   injected deletion. `drain_case` now calls `wait_settled` first.
5. **Two recovery steps measured too early.** After restoring CoreDNS (Lab 24)
   and the webhook backend (Lab 25), a ready Pod and a listed endpoint were not
   enough: each node's proxy rules had to be rewritten first, so the first
   measurement failed. Both labs now wait for the endpoint and then for the
   operation itself to succeed, and both cards explain why.
6. **Output quality.** A failed request in Lab 24 printed a 25-line Python
   traceback; its `probe` helper now prints one line and keeps a nonzero exit.
   `openssl` progress output in Lab 25's setup is silenced.

## Unification with the existing labs

The new definitions were audited against Labs 10–21 and aligned where they had
drifted:

| Convention checked | Source | Action |
| --- | --- | --- |
| Per-lab `kNN` wrapper pinning kubeconfig, context, namespace and a 10 s request timeout | Labs 19–21 | Lab 25's helper reduced from 15 s to 10 s; `kNNsys` added only where a lab must also reach a second namespace, as Lab 13 does inline |
| Namespace `ce-labNN`, container names `ce-labNN-*` | Labs 17–21 | Already matched; Lab 25's second namespace follows the same prefix |
| Manifest `command:` as a block list, `resources` of 20m CPU / 16Mi memory with a 128Mi limit, `readinessProbe` after `resources`, `env` last | Labs 19–21 | All new manifests rewritten; Lab 23's 32Mi requests reduced to 16Mi |
| Idle helper Pods run `python -c 'import time; time.sleep(86400)'` | Lab 20 | Replaced `sleep infinity` in Labs 23 and 24 |
| No `metadata.namespace` in fixtures; the helper supplies it | Labs 10–21 | Removed from all seven Lab 25 manifests |
| Scripts mounted at `/scripts` from a `<topic>-scripts` ConfigMap | New mechanism, used consistently | Lab 25's `admission-code` at `/code` renamed to `admission-scripts` at `/scripts` |
| `--wait=true --timeout=30s` for Pod deletions | Labs 19–20 | Lab 25's 60 s Pod deletions reduced to 30 s |
| Docker labs: `docker create` / `docker cp` / `docker start`, `ce-labNN-*` filters in reset | Lab 17 | Lab 22 already matched |
| Teaching applications are Python on `python:3.12-slim`, inline when short and a file in `files/` when long | Labs 12, 15, 17, 19-21 | Lab 22's trivial PID 1 application moved inline into its `docker create` command, leaving four fixtures; the file-plus-ConfigMap route used by Labs 23-25 is now written down in lab-design.md |

The one deliberate difference is Lab 24's `probe` helper, which catches the error
and prints a single line instead of letting a failed lookup print a Python
traceback. That path is exercised on purpose in the CoreDNS outage step.

## Theory-section audit

Each new card was re-read against the five requirements in
[lab-design.md](../lab-design.md) and rewritten where it fell short:

- **Fixture numbers were missing.** Lab 22 now states the 40 inherited orphans
  and the bursts of 40 and 200 against the 64-PID budget; Lab 23 states the two
  replicas, the two-second request path against an immediate `/healthz`, the 25
  requests per second and the deletion at about four seconds; Lab 24 names the
  two clients, the four names measured and where CoreDNS forwards; Lab 25
  describes both namespaces, the single backend replica and the 443→8443 Service.
- **Arithmetic the questions ask for was implicit.** Lab 22 now gives the budget
  equation, and Lab 24 gives both cost formulas, so the amplification factor can
  be calculated before running.
- **Evidence that needed decoding was only in the measurement key.** The cards
  now explain `pid1_cmdline` versus `comm`, the `ReplicaFailure` condition, the
  refused-versus-timeout distinction and what an `unavailable` counter means.
- **Structure.** Every section now runs mechanism → what the measurement means →
  the fixture → how to read the evidence → the rule the transfer question needs,
  with no paragraph over about 65 words, matching the density of Labs 19–21.

## Not yet validated

- **The Vagrant VM path.** These runs used a different Docker engine, host
  architecture and kubectl build from the teaching VM. `ps -eo pid --no-headers`
  and `date +%T.%3N` are GNU syntax exercised only inside the VM's userland, and
  the Ansible setup/verify/reset wrappers were not run against a VM.
- **AMD64.** Everything above was measured on ARM64.
- **Image preloading.** `kind load` could not be used on this host's containerd
  image store, so Pods pulled `python:3.12-slim` from the registry. The VM's
  `load-lab-images-into-kind.sh` path is therefore untested for these labs.
- **Note on running the gate from macOS.** `tests/test_reset.py` and
  `tests/test_process_reset.py` need GNU `find -printf` and `/proc`, so
  `scripts/validate.sh` refuses to run on macOS. It was run in a Linux container
  instead; run it on the Linux or WSL controller before release as well.
- **Print edition.** `docs/chaos-labs.pdf` still contains 22 labs. Regenerate it
  with `python3 scripts/render-labs-pdf.py` where ReportLab and the DejaVu fonts
  are available, then inspect the pages.
- **Timing margins.** Lab 23's graceful case recorded one failure on one run and
  none on another; its solution treats that as a result about the application,
  not as proof about the race, and points to the in-flight count and endpoint
  conditions instead. Lab 24's external-name comparison needs working outbound
  DNS from the VM.
- **Certificate trust.** Lab 25 generates one self-signed certificate at setup
  and installs it as both the serving certificate and the `caBundle`. It is
  valid for 365 days and recreated by every setup; it is not a model for
  production certificate management.

## Capacity

These labs add three more possible kind clusters in the same VM. Reset finished
labs before starting others; the VM's 16 GiB and 4 vCPUs are shared, and resource
independence between labs is not a performance guarantee.
