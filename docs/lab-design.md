# Lab authoring contract

The catalog contains 27 labs: seven container labs and 20 Kubernetes labs.
Use consecutive IDs from 00 through 26. Standalone
general Linux and chaos-planning exercises are outside this catalog.

Each lab tests one container or Kubernetes question using controlled comparisons
and cites the broader `chaos-theory.md` reference.
Depth comes from explaining evidence, checking a causal mechanism and recognizing
the limits of the conclusion. Extra services, unrelated tool tours and optional
command branches are not required for depth.

## Keep the learner's work direct

The exercise is to predict, observe and explain a mechanism. Do not make shell
programming a prerequisite for that work.

- Keep the command that changes the experimental variable visible, including its
  value and target. Prefer a direct command or a supplied manifest over text rewriting.
- Use native output (`describe`, `logs`, `get`, `cat`) when it exposes the needed
  evidence clearly. A short, necessary filter is fine; a pipeline is not a learning goal.
- Supply repeated sampling, arithmetic, waits and diagnostic formatting in a small
  local helper when the inline code distracts from the experiment. Explain its
  inputs, target, measurement and limits in `in_this_lab`. Keep its source in
  `files/exercise.sh`; the learner sources it once in each shell that needs it.
- Helpers must retain raw evidence and distinguish failure, missing data and a
  successful observation. A wait reaching its limit must not print a success claim.
- Keep one setup command and the existing lifecycle. Do not add a new runner,
  configuration language or dependency merely to shorten a command.
- Questions ask what changed, why it changed and what the evidence establishes.
  Solutions answer those questions directly, without teaching incidental parsing syntax.

`k`, `ksys` and `h`, where used, are supplied wrappers around kubectl for that
lab's private kubeconfig and namespace. They do not change the Kubernetes operation.
The helper implementations are optional reading for learners and maintained code
for authors; syntax checks and file-installation tests cover them too.

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
for the earlier catalog, and [the chaos expansion review](reviews/chaos-expansion-review.md)
and [the security expansion review](reviews/security-expansion-review.md) record
later additions using the original IDs in [the numbering map](lab-numbering.md).
Automated content checks support these reviews; they
cannot judge whether an explanation is sufficient for a learner.

`task.brief.theory` is the shared theory text for a lab's terminal card and generated
guide; it must teach the relevant subset of `chaos-theory.md`. `readings` decodes the
signals; `evidence` supplies a blank results table. `commands` contains one core
procedure, including normal recovery. `fallback` contains only exceptional
cleanup. `transfer` asks one reasoning question about a changed condition; its
answer lives in `transfer_solution`, shown only by the solution.

`task.brief.main_lesson` supplies the section "Main lesson to learn in this lab".
Write one short paragraph, usually 50–80 words: lead with the central mechanism,
highlight the distinction or evidence that matters most, and finish with the
conclusion to retain. Synthesize the theory already taught; keep its essential
conditions and scope. Do not introduce commands, new prerequisites or claimed
measurements. This takeaway follows the full theory in the question card, guide
and PDF, and opens the solution card for quick review.

Each procedure step has a clear name, its terminal, a complete `run` block and a
neutral `record` instruction. Put the observation beside the command that
produces it. Split different faults and normal recovery into separate steps;
include variable initialization, helper definitions, measurements and recovery
commands before asking the learner to use their results. A helper invocation
must identify its case and expose the evidence needed to answer the question.

`task.answer_with` is a numbered list of direct questions. `solution` is a list
with one answer in the same position for every question. `record` keeps expected
outcomes out of the question card. Setup/verify/SSH and final solution/reset
commands are rendered consistently by the shared templates; do not repeat them
in individual labs.

Three surfaces render from the same definition, and each carries a different
subset:

| Surface | Command | Contains |
| --- | --- | --- |
| Question card | `./lab.sh NN setup`, `./lab.sh NN question` | `title`, `question`, `in_this_lab`, the numbered `answer_with` prompts, `theory`, `main_lesson`, and the numbered steps with their `run` and `record`, plus the `fallback` commands when a lab has them |
| Solution card | `./lab.sh NN solution` | `main_lesson`, `answer_with` with each `solution`, `transfer` and `transfer_solution`, then every step again with `expect`, and `verify_note` |
| Learner guide | `docs/chaos-labs.md` | everything, including `prerequisites`, `predict`, `in_this_lab`, `readings` and the blank `evidence` table |

The terminal card opens by stating what the lab asks: the `question`, what the
fixture is, and the numbered questions the learner will answer. The theory, main
lesson and commands follow. `prerequisites`, predictions,
the measurement key, `theory_source` and the results table live in the guide,
and the answers live on the solution card, which repeats the same numbered
questions in the same order. A `record` instruction names a row of the
guide's table, so keep `evidence.rows` and the `record` leads identical.

Keep every surface scannable. A `readings` entry is one sentence, about twenty
words, that says what the signal means and how to misread it. A `record`
instruction is a short lead naming the evidence row, then the values separated
by semicolons, rather than a sentence listing them. The terminal solution
repeats every step under `STEPS AND COMMANDS FOR THESE ANSWERS`, so the answers
and the commands that produce them are in one place.

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
| 00–01 | §§5.2–5.7.1 | Small namespace sandbox and a 32 MiB shared tmpfs, without filling the VM disk |
| 02 | §§5.8–5.11 | Tiny echo dependency with one versus four known sequential exchanges; host tc enters its network namespace |
| 03 | §§10.4, 10.5.1–10.5.2 | Ownership, PDB eviction versus direct deletion, HTTP sampling and an unmatched Service selector |
| 04 | §§10.4.4, 10.5.3–10.5.4 | TCP versus HTTP readiness; 300 ms peer and 1 s probe budgets; eligibility versus restarts |
| 05 | §§11.2, 11.4.1–11.4.3 | Monotonic startup deadline; delayed, unschedulable and selector faults; pre-cleanup diagnostics and healthy sample SLI |
| 06 | §§12.1.1–12.1.3, 12.3.1–12.3.2 | Cordon versus kubelet loss; explicit tolerations; Lease, taint, identity and runtime timeline |
| 07 | §§5.13.1–5.13.2 | Same worker; signal delivery and stop budget varied separately; completion marker and exit evidence |
| 08 | §§5.13.3–5.13.4 | Dedicated named volume; replacement, numeric ownership and read-only access compared without host bind mounts |
| 09 | §§10.6.1–10.6.2 | Impossible CPU request versus bounded container OOM; UID-specific events and previous logs |
| 10 | §§10.7.1–10.7.2 | Same client context; wrong name, wrong targetPort and loopback binding isolated separately |
| 11 | §§10.8.1–10.8.2 | Every consumer queried; environment freshness, rollout stall and explicit template/configuration recovery |
| 12 | §§5.14.1–5.14.2 | Explicit reaper instead of `--init`; one 64-PID budget consumed by zombies and then by live processes |
| 13 | §§10.9.1–10.9.2 | Two-second requests and a 25/s probe; in-flight count at SIGTERM; shutdown behaviour, preStop and grace budget each varied alone |
| 14 | §§10.10.1–10.10.2 | CoreDNS request counters read per lookup; ndots, trailing dot and an absent name; resolver removed, not the data path |
| 15 | §§12.4.1–12.4.2 | Self-signed webhook scoped by namespace label; backend removed under Fail, then compared with Ignore |
| 16 | §§5.15.1–5.15.2 | One image run four ways; boundaries read from `/proc/self/status` and compared with `docker inspect` |
| 17 | §§12.6.1–12.6.2 | Six named CIS controls read from four interfaces; one file mode, one API server flag and one binding changed and reverted |
| 18 | §§12.5.1–12.5.2 | One namespace relabelled through the levels and modes; the violating Pod created before the level is applied |
| 19 | §§10.11.1–10.11.2 | Two identical clients differing only in the token mount; one probe asking two namespaces per run |
| 20 | §§12.7.1–12.7.2 | One Secret read through four surfaces, including etcd on the node; rotation measured rather than assumed |
| 21 | §§12.8.1–12.8.2 | Two clients differing only in one label; each policy applied alone and the failure timed against the caller's budget |
| 22 | §§12.9.1–12.9.2 | Three non-overlapping Roles in one namespace; the escalation performed, and four authorization answers compared |
| 23 | §§10.12.1–10.12.2 | One initializer, independent readiness/progress markers, and manifests differing only in startup protection |
| 24 | §§10.13.1–10.13.2 | One static local PV, contradictory consumer placement, PVC protection and retained-marker recovery |
| 25 | §§12.10.1–12.10.2 | Small sleeping Pods; defaults, per-container bounds and aggregate quota tested separately |
| 26 | §§12.11.1–12.11.2 | Exact toy etcd records, a forced rewrite and missing-key recovery through a private static API server |

The lab path samples the selected chapters; it is not an exhaustive exercise for
every tool or claim in the reference. The source contains historical examples,
editorial qualifications, and some older unqualified summaries. Use the mechanisms
with these qualifications:

- CPU weights are relative preferences under contention. Quotas are bandwidth ceilings, not reservations. The [kernel's cgroup v2 reference](https://docs.kernel.org/admin-guide/cgroup-v2.html) defines the actual files used here.
- An exit status alone cannot diagnose OOM. Use matching unit, kernel and process evidence; kernel OOM killing uses SIGKILL, not SIGTERM.
- [Kubernetes tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/) allow explicit eviction delays. Lab 06's 20 seconds is a fixture setting, not a claim about a cluster default or total recovery time.
- `imagePullPolicy: Always` can reuse cached layers. Lab 05 measures warm startup and does not claim cold-image coverage.
- Zombie entries occupy PIDs in the cgroup [`pids` controller](https://docs.kernel.org/admin-guide/cgroup-v2.html#pid). Orphans go to the nearest ancestor [subreaper](https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html), or otherwise PID 1. Lab 12 uses an explicit reaper so the collection mechanism is measured.
- A `preStop` hook is included in [`terminationGracePeriodSeconds`](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/), not added to it. Lab 13 measures the endpoint-removal interval; a run that records no failed request missed that interval and is not evidence against the race.
- The glibc resolver falls back to the remaining candidates after any failed attempt, so `ndots` changes the order, not the total, for names that resolve nowhere. Lab 14 counts CoreDNS requests, which include cache hits, and does not claim musl behaviour.
- Admission [`failurePolicy`](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#failure-policy) governs call failures, not explicit policy rejections. `Ignore` lets other checks continue. Lab 15 scopes its webhook by namespace label and to `CREATE` on Pods.
- A benchmark scan is a comparison, not enforcement. Lab 17 reads six [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes) controls from the running configuration rather than from files on disk, and reverts every change it makes.
- Lab 16 measures boundaries; it does not exploit them. `--pid=host` and `--privileged` expose the lab VM's own processes and devices, because container isolation is a kernel boundary rather than a virtual-machine boundary.
- [Pod Security admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/) checks the fields of a Pod at creation. Lab 18 shows that labelling a namespace warns about, but does not evict, a Pod that already violates the level, and that `warn` creates every object it reports.
- A `403` in Lab 19 is an authorization result from [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/). Removing the projected token changes the identity to `system:anonymous`, which exists because anonymous authentication is enabled by default; it does not remove the network path to the API server.
- Lab 20 distinguishes workload permissions from the [kubelet's own authorized Secret access](https://kubernetes.io/docs/reference/access-authn-authz/node/). [Secret volume updates](https://kubernetes.io/docs/concepts/configuration/secret/#using-secrets-as-files-from-a-pod) are eventual; an API update alone does not prove the consumer has reloaded it.
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/#the-two-sorts-of-pod-isolation) combines allowed traffic per direction; both isolated sides must allow a connection. Traffic from the Pod's own node and replies to allowed connections are exceptions to isolation. Lab 21 measures its plugin's drop behaviour rather than promising that every implementation reports failures identically.

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
boundary handling, stale metrics after submission failure, fault observation and
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

The VM also hosts the permanent Rancher management installation on RKE2. Its
data, certificates and `~/.kube/rke2.yaml` are outside lab workspaces. Destructive
experiments keep their private kind clusters; they must not target RKE2, Rancher,
or management's bundled client. See [platform setup](rancher-rke2.md).

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
Central cleanup removes the workspace last on both setup and reset.

Never prune Docker globally, delete shared image caches or change another lab's
systemd unit, port, namespace or kubeconfig. Use named units/containers and private
configuration files. Shared kernel resources and capacity remain common to the VM;
resource independence does not promise performance isolation.

Install fixtures through Ansible copy/template tasks. The lifecycle and offline
cards use Bash, Vagrant and Ansible. Python is limited to teaching applications
and optional authoring checks, not a custom lifecycle controller.

Teaching applications use the cached `python:3.12-slim` image and the VM's
`python3`, and reach their destination in one of three ways. A program of about
ten lines or fewer is written inline in the manifest's `command`, as Labs 09-11
do. A longer program stays as a file under the lab's `files/` directory; setup
copies it into a Docker container with `docker cp` (Labs 07 and 12) or installs
it into the cluster as a `<topic>-scripts` ConfigMap mounted at `/scripts`
(Labs 13-15). Programs that run on the VM itself are executed from the
workspace directly (Lab 05). Choose the shortest of these that keeps
the program readable; do not embed fifty lines of Python in a YAML string.

Run `bash tests/test-lifecycle.sh` for command routing and failure propagation.
The test suite also exercises real Ansible reset tasks against isolated test
resources. See `docs/reviews/isolation-review.md` for results and live-test limits.
