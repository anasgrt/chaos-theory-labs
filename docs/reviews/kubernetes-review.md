# Kubernetes lab review

> Historical review: this report describes an earlier revision. The current catalog
> contains 27 container and Kubernetes labs, renumbered 00 through 26. Lab numbers
> and counts below use the original catalog and are historical evidence, not current
> setup instructions. See [the numbering map](../lab-numbering.md) for retained labs.

Historical teaching-content review. For the current single-VM lifecycle, see
[isolation-review.md](isolation-review.md). Shared-cluster setup notes below are superseded.

The expanded sequence keeps Labs 10–14 and their dependencies. Each lab now uses
several controlled comparisons to answer one central question. The main theory,
question card, prediction, evidence table, commands and solution were reviewed
together. Source behavior was checked against Kubernetes and etcd documentation
linked beside the explanations in `chaos-theory.md`.

## Alignment review

| Lab | Added comparisons | Theory that supports the answer | Recovery evidence |
| --- | --- | --- | --- |
| 10 | Ownership chain; rejected eviction versus direct deletion; unmatched Service selector | §§10.5.1–10.5.2 explain UID, reconciliation, PDB scope and endpoint eligibility | Three Ready Pods, three eligible endpoints, HTTP success, temporary PDB removed |
| 11 | TCP versus one-second HTTP readiness; 400 ms and 1400 ms against different caller budgets | §§10.5.3–10.5.4 explain probe actions, thresholds and direct Pod discovery | Toxic removed, same UID/restart counts within the HTTP comparison, readiness and peer pings restored, experimental Pod/forward removed |
| 12 | Delayed, unschedulable and wrongly selected startup fixtures; three restored healthy trials | §§11.4.1–11.4.3 explain measurement boundaries, stage diagnosis, evidence freshness and the sample denominator | Healthy manifest restored, fresh per-trial evidence, Pod and Service absent after cleanup |
| 13 | Cordon/delete/uncordon before kubelet loss; Lease and runtime timeline | §§12.3.1–12.3.2 explain placement preferences, heartbeat detection, taint timing and fencing limits | Workers supervised and uncordoned, replacement Ready, obsolete runtime container removed if replacement occurred |
| 14 | Scale with quorum, attempt writes without it, inspect persisted intent before restoration | §§12.3.3–12.3.4 explain voter counts, leader transitions, asynchronous convergence and uncertain write results | Three healthy etcd endpoints, explicit two-replica target converged, recovered ConfigMap value and successful HTTP |

The source's older claims about terminal Pod phases, image caching, refresh timing,
node detection and etcd majority acknowledgements were corrected where they would
contradict these experiments. Historical book experiments remain identified as
historical examples rather than claimed results from these fixtures.

## Issues found and fixed during review

- The baseline ReplicaSet could adopt the standalone slow Pod. Its ownership
  selector now additionally requires `component=baseline`; Service discovery still
  includes the experimental Pod. A generated-manifest test checks both relationships.
- A diagnostic event from an earlier Pod with the same name could be mistaken for
  current evidence. The startup checker filters events by the current UID and
  explicitly records failed diagnostic reads.
- Old diagnostic files could be reused after an early checker failure. Each new
  invocation clears only its generated `run-*.json` files before contacting Docker.
  The procedure preserves each fault's evidence separately.
- A reset runs before setup. Lab 14 now handles an absent cluster/helper and partially
  prepared workloads before attempting to restore the two-replica baseline.
- A fixed etcd sleep did not confirm injection. The helper now waits for the selected
  runtime container to stop. The learner checks both surviving members for leader evidence.
- A stored port-forward PID could refer to a shell wrapper or a reused process.
  Lab 11 launches kubectl directly and checks the command identity before cleanup.
- The earlier three-minute node observation description excluded API call duration.
  The card now states the actual 18-sample procedure and explains timing uncertainty.
- Live provisioning exposed an invalid Goldpinger image tag: `v3.11.3` does not
  exist in the registry. All references now use the published `3.11.3` tag. Its
  multi-architecture image also removes the need for the previous ARM64 source build.
- Peer/readiness observation helpers and HA reset lookups could hide API failures.
  They now return failure instead of treating an unavailable query as empty evidence;
  regression tests exercise those error paths.
- Lab 10 verification now checks three eligible endpoints, successful HTTP and the
  absence of the temporary PDB in addition to replica count and workload permissions.
- Live HA recovery stalled while a kubelet repeatedly contacted its local API server,
  whose etcd member was stopped. Setup now routes control-plane kubelets through the
  HA API load balancer. The logs also showed blocked mirror-Pod deletion, a behavior
  described in a [related Kubernetes report](https://github.com/kubernetes/kubernetes/issues/139502).
  The full sequence passed after this fixture change; moving manifests alone is not
  considered proof of recovery.
- The final HA restoration step now refuses to overwrite configuration until both
  endpoint health and state readback have succeeded. A regression test covers
  missing or unsuccessful prerequisites.

## Validation and limits

Local validation includes 17 passing regression tests and covers all 17 labs and
34 cards, embedded Bash/Python/YAML syntax,
the generated Markdown guide, exact Kubernetes theory-section references, and the
startup checker's deadline and diagnostic behavior. Generated-manifest tests execute
fixture creation under an isolated HOME with a stub kubectl; they do not simulate
Kubernetes reconciliation. Ansible syntax and actual Ansible template rendering are
checked separately from the offline renderer.

The generated Kubernetes manifests also passed kubeconform strict validation against
Kubernetes 1.35.0 schemas: 21 resources, no invalid or skipped resources. Schema
validation checks API structure, not scheduling or observed fault behavior. The lab
PDF is regenerated and visually reviewed after content changes.

Live checks on 2026-09-18 used the actual YAML setup, verify, procedure and reset
commands from an Ubuntu 24.04 AMD64 runner against kind v0.33.0 / Kubernetes
v1.37.0 on Docker Desktop's Linux engine. The runner shared the engine's network
so the lab's node-IP requests used the intended path. These were real Kubernetes
controllers and container runtimes, not mocked reconciliation.

| Lab | Observed result |
| --- | --- |
| 10 | Eviction returned the expected PDB `TooManyRequests` rejection. Direct deletion replaced the UID; 100/100 sampled HTTP requests succeeded. An unmatched selector produced zero eligible endpoints and HTTP failure; restoration returned three endpoints and HTTP success. |
| 11 | All three peers passed at 100 ms and timed out at 400 ms. TCP readiness remained true. HTTP readiness stayed true at 400 ms and became false at 1400 ms, with unchanged UID and zero restarts within that phase. Removing the toxic restored readiness and peer success. Both probe configurations were repeated. |
| 12 | Seven trials had seven distinct Pod UIDs. The normal trial passed; delayed, unschedulable and wrong-selector trials each recorded a completed 30-second miss with the correct distinguishing diagnostics. All three restored trials passed. Events matched each current Pod UID, and cleanup removed the Pod and Service. |
| 13 | Cordon preserved the existing UID/runtime; deletion placed the replacement elsewhere, and uncordon did not move it back. Stopping kubelet froze Lease renewal, the node became unavailable, and a replacement appeared while the original runtime remained alive. Recovery restored four Ready, uncordoned nodes and removed the obsolete container. The sampling log contains an extended observation gap, so it is not used to claim exact recovery latency. |
| 14 | After the API-path fix, the complete sequence passed without intervention. One stopped voter allowed the ConfigMap write and scale from two to three Ready replicas. Two stopped voters produced nonzero write/scale exits while HTTP stayed 200. All three members recovered; readback showed `one-down` and three replicas before restoration to `recovered` and two Ready replicas. Final etcd health and HTTP passed. Reset also recovered a separately stopped member and restored the baseline. |

These setup/verify/reset runs predate the independent VM lifecycle. Current
provisioning coverage is recorded in [isolation-review.md](isolation-review.md).
A published ARM64 image and valid manifests do not establish live ARM64 coverage.

`chaos-labs.md`, terminal cards and the lab PDF share the YAML definitions.
`chaos-theory.md` is the maintained theory source; the old theory PDF is an archival
export and is not evidence of the updated content.
