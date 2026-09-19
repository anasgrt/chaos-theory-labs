# Lab authoring contract

Each lab tests one question from `chaos-theory.md` using controlled comparisons.
Depth comes from explaining evidence, checking a causal mechanism and recognizing
the limits of the conclusion. Extra services, unrelated tool tours and optional
command branches are not required for depth.

## A question card must stand on its own

Before showing commands, explain:

1. The terms used in the question, with only the mechanisms needed for this lab.
2. Why changing the selected variable could change the measured outcome.
3. The actual fixture configuration, including timeouts, limits and units.
4. How to interpret every measurement needed for the answer, including failure or missing evidence.
5. The rule needed for the transfer question. New facts must not appear for the
   first time in its solution; the learner should apply a taught mechanism to a
   changed condition.

The learner should not need the solution to decode `cpu.max`, distinguish a
watchdog from a handled timeout, calculate an amplification factor, or understand
which operation a readiness check tests. Teach those rules first. Leave the
learner to predict, measure and explain their particular result.

Review the actual fixture and measurement code when checking these explanations.
State the timer boundaries, units, arithmetic and meaning of success explicitly.
Do not describe a later command's exit status as the outcome of an earlier write,
or treat configured limits and accumulated counters as proof of current enforcement.
The [question-theory review](reviews/question-theory-review.md) records the coverage audit
for all 22 labs. Automated content checks support this review; they cannot judge
whether an explanation is sufficient for a learner.

`task.brief.theory` is the shared theory text for a lab's terminal card and generated
guide; it must teach the relevant subset of `chaos-theory.md`. `readings` decodes the
signals; `evidence` supplies a blank results table. `commands` contains one core
procedure, including normal recovery. `fallback` contains only exceptional
cleanup. `transfer` asks one reasoning question about a changed condition; its
answer lives in `transfer_solution`, shown only by the solution.

`solution` and each command's `expect` explain conditional outcomes. Never present
expected timings or counts as collected measurements. `verify` checks readiness
to begin; `verify_note` describes the experiment's recovery evidence. Some labs
remove their objects during recovery, so these are intentionally different checks.

## Theory mapping and adaptations

The map at the start of `chaos-labs.md` is generated from the lab citations. The
source retains original section numbers although its chapter headings have been
renumbered. Do not infer a section number from the displayed chapter number.

| Labs | Main theory | Deliberate adaptation |
| --- | --- | --- |
| 00–01 | §§1.3, 1.5, 2.5 | Explicit baselines, bounded Redis failure, separate application timeout and watchdog |
| 02–03 | §§2.3–2.6 | Bounded cgroup OOM; explicit systemd start limits rather than historical defaults |
| 04 | §§3.2, 3.3.5 | Same fixed CPU job, one competitor, cgroup v2 quota and enforcement evidence |
| 05–06 | §§5.2–5.7.1 | Small namespace sandbox and a 32 MiB shared tmpfs, without filling the VM disk |
| 07 | §§5.8–5.11 | Tiny echo dependency with one versus four known sequential exchanges; host tc enters its network namespace |
| 08–09 | §§6.2–6.5 | Book server's close error path and a narrowly scoped libseccomp denial |
| 10 | §§10.4, 10.5.1–10.5.2 | Ownership, PDB eviction versus direct deletion, HTTP sampling and an unmatched Service selector |
| 11 | §§10.4.4, 10.5.3–10.5.4 | TCP versus HTTP readiness; 300 ms peer and 1 s probe budgets; eligibility versus restarts |
| 12 | §§11.2, 11.4.1–11.4.3 | Monotonic startup deadline; delayed, unschedulable and selector faults; pre-cleanup diagnostics and healthy sample SLI |
| 13 | §§12.1.1–12.1.3, 12.3.1–12.3.2 | Cordon versus kubelet loss; explicit tolerations; Lease, taint, identity and runtime timeline |
| 14 | §§12.1.1, 12.1.4, 12.3.3–12.3.4 | Quorum and leader evidence; configuration writes versus convergence versus HTTP; post-timeout readback |
| 15 | §§1.2.3, 12.1.4 | Countable HTTP 503 failure isolates layered retries without claiming to reproduce a full retry storm |
| 16 | §§1.3, 2.5; Appendix C | One measurable experiment plan, including analysis and recovery |
| 17 | §§5.13.1–5.13.2 | Same worker; signal delivery and stop budget varied separately; completion marker and exit evidence |
| 18 | §§5.13.3–5.13.4 | Dedicated named volume; replacement, numeric ownership and read-only access compared without host bind mounts |
| 19 | §§10.6.1–10.6.2 | Impossible CPU request versus bounded container OOM; UID-specific events and previous logs |
| 20 | §§10.7.1–10.7.2 | Same client context; wrong name, wrong targetPort and loopback binding isolated separately |
| 21 | §§10.8.1–10.8.2 | Every consumer queried; environment freshness, rollout stall and explicit template/configuration recovery |

The lab path samples the selected chapters; it is not an exhaustive exercise for
every tool or claim in the reference. The source contains historical examples,
editorial qualifications, and some older unqualified summaries. Use the mechanisms
with these qualifications:

- CPU weights are relative preferences under contention. Quotas are bandwidth ceilings, not reservations. The [kernel's cgroup v2 reference](https://docs.kernel.org/admin-guide/cgroup-v2.html) defines the actual files used here.
- An exit status alone cannot diagnose OOM. Use matching unit, kernel and process evidence; kernel OOM killing uses SIGKILL, not SIGTERM.
- [systemd start limits](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html#StartLimitIntervalSec=interval) count starts, not only crashes. Fixtures explicitly declare their limits.
- [Kubernetes tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/) allow explicit eviction delays. Lab 13's 20 seconds is a fixture setting, not a claim about a cluster default or total recovery time.
- `imagePullPolicy: Always` can reuse cached layers. Lab 12 measures warm startup and does not claim cold-image coverage.
- etcd quorum is `floor(n/2) + 1` of configured voting members. [Majority loss prevents writes](https://etcd.io/docs/v3.7/op-guide/failures/); stopped members do not automatically leave membership.
- NGINX only retries the configured conditions. Lab 15 explicitly enables [`http_503` and two total tries](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_next_upstream), using GET requests.

## Validation

Use Linux or WSL for the full suite, including process identity through `/proc`.
Install Ansible, Bash and jq, then install `requirements-dev.txt` into a Python
environment. After changing definitions, refresh the generated guide and validate:

```bash
python3 scripts/render-labs.py
bash scripts/validate.sh
```

The validation entry point resolves paths from its own location, requires the
integration-test dependencies, and checks content, guide freshness, lifecycle
routing, all three Ansible playbooks, identity rejection and the regression suite.
It does not connect to the VM. Regenerate and visually inspect the PDF after
changing printed content, using the instructions in [the README](../README.md#validate-changes).

Kubernetes definitions list exact `theory_sections`; the checker requires those
headings to exist in `chaos-theory.md`. Keep the main source, standalone card,
predictions, results table, procedure and solution aligned when adding a task.
The baseline Goldpinger ReplicaSet selects `component=baseline` in addition to
`app=goldpinger`, while the Service selects only the application label. This keeps
the experimental standalone Pod discoverable without allowing ReplicaSet adoption.

The static checker parses every definition, renders both cards for every lab,
checks that theory is present and solutions are separate, validates shell and
embedded Python/YAML syntax, and detects guide drift. Tests cover deadline
boundary handling, stale metrics after submission failure, retry accounting and
offline question rendering. These checks do not replace live experiments.

For live acceptance, provision one VM, then set up labs in arbitrary order.
Complete each procedure and check recovery. Keep another lab running with a marker
and verify that setup/reset preserve its files, containers, services and cluster.
Test reset before first setup, repeated reset, interrupted setup and broken
Kubernetes APIs. Check AMD64 and ARM64 before claiming both were tested.

## Isolation contract

Vagrant defines one VM, `chaos`, with guest hostname `chaos-labs`. Provisioning
installs shared tools once. Per-lab setup, verify and reset run Ansible in that VM;
they must never destroy, halt or reprovision it. The inventory/hostname check
rejects connections to another machine.

Each `labs/NN-topic/` directory owns its `lab.yml` and optional `files/` directory.
Declare plain filenames under `files:`; Ansible installs them in `~/labs/labNN/`.
No definition may depend on another lab's files or resources. Discovery rejects
duplicate IDs. Use `ansible/files/` only for reusable infrastructure definitions.

`labs.yml` calls `tasks/reset.yml` before setup and for public reset. Declare owned
systemd units under `units:` using `ce-labNN` names. Custom `reset` steps remove
only that lab's containers, mounts, recorded processes and fault rules; they must
work before the first setup and after partial failures. Kubernetes definitions
declare `kubernetes: true`; central cleanup deletes only cluster `labNN` using
kind, without querying the Kubernetes API. Keep its kubeconfig in its workspace.
Central cleanup removes the workspace last. Only Lab 16 preserves it on setup.

Never prune Docker globally, delete shared image caches or change another lab's
systemd unit, port, namespace or kubeconfig. Use named units/containers and private
configuration files. Shared kernel resources and capacity remain common to the VM;
resource independence does not promise performance isolation.

Install fixtures through Ansible copy/template tasks. The lifecycle and offline
cards use Bash, Vagrant and Ansible. Python is limited to teaching applications
and optional authoring checks, not a custom lifecycle controller.

Run `bash tests/test-lifecycle.sh` for command routing and failure propagation.
The test suite also exercises real Ansible reset tasks against isolated test
resources. See `docs/reviews/isolation-review.md` for results and live-test limits.
