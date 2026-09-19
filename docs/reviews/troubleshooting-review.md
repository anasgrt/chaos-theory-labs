# Container and Kubernetes expansion review

Historical teaching-content review. For the current single-VM lifecycle, see
[isolation-review.md](isolation-review.md). Shared-cluster setup notes below are superseded.

Reviewed 18–19 September 2026. This extends the earlier Kubernetes review with five
new labs while preserving existing lab numbers and procedures.

## Alignment

| Lab | Main theory | Question-card preparation | Required comparison |
| --- | --- | --- | --- |
| 17 | §§5.13.1–5.13.2 | PID 1, shell exec, TERM receipt, cleanup budget, exit evidence | Wrapper/5 seconds; exec/5 seconds; exec/1 second |
| 18 | §§5.13.3–5.13.4 | Container versus volume lifetime, numeric UID/GID, directory permissions, mount mode | Replacement; wrong owner; corrected owner; read-only; writable recovery |
| 19 | §§10.6.1–10.6.2 | Requests versus limits, scheduling conditions, container termination and previous logs | Healthy; impossible CPU request; bounded OOM; healthy restoration |
| 20 | §§10.7.1–10.7.2 | DNS, Service port/targetPort, endpoint conditions, listening interfaces | Wrong namespace name; wrong targetPort; loopback bind; recovery after each |
| 21 | §§10.8.1–10.8.2 | Environment snapshots, Pod-template revisions, rollout availability/progress, separate ConfigMaps | Configuration edit; consumer restart; bad readiness; undo; explicit configuration restoration |

Each question includes the relevant mechanisms before commands, explains its
measurements, and asks for predictions, recorded evidence and a transfer answer.
The solution remains separate. The main theory includes diagnostic comparisons
and primary documentation links. The SIGTERM/OOM contradiction in the rapid
review answer key was also corrected.

## Live results

Executed the actual setup, verify and procedure commands using an Ubuntu 24.04
review container against Docker Desktop's Linux engine, kind v0.33.0 and
Kubernetes v1.37.0 on AMD64. The new Kubernetes fixtures ran in their dedicated
namespaces on Lab 10's four-node cluster.

- **17:** The wrapper worker was a child and never logged TERM receipt. It exited
  137 with `OOMKilled=false` and no cleanup file. With exec and five seconds, the
  worker was PID 1, received TERM, completed cleanup and exited 0. With one second,
  it received TERM but exited 137 before writing the completion file.
- **18:** The volume file survived replacement; the original writable-layer file
  did not. UID 10001's first write failed with permission denied and exit 2.
  Correcting the directory owner produced exit 0. A read-only mount produced
  `Read-only file system`, exit 2 and `RW=false`. A writable mount restored the
  write while retaining the original volume file; the test volume was removed.
- **19:** The oversized CPU request produced `Unschedulable` and insufficient-CPU
  events without a node assignment. The memory experiment was scheduled and
  recorded `OOMKilled`; previous logs retained the 96 MiB allocation message.
  The restored Pod became Ready with the baseline resources and zero restarts.
- **20:** Correct name, Service IP and Pod IP returned HTTP 200. The wrong name
  failed resolution while the IP path worked. Wrong targetPort preserved DNS
  and direct-Pod HTTP but broke Service HTTP. Loopback binding allowed local HTTP
  while remote Pod HTTP and readiness failed. Restoring the listener returned
  Service HTTP 200 and a Ready endpoint.
- **21:** Editing the ConfigMap kept existing UIDs and version-one responses.
  Restart created version-two consumers. Port 9999 stalled the rollout with
  `ProgressDeadlineExceeded`; two old replicas stayed available and the unready
  process still answered direct HTTP on 8080. Undo repaired the probe while
  retaining version-two. Explicit configuration restoration and restart returned
  two Ready version-one consumers.

After the procedures, Kubernetes verify checks passed again. For all five labs,
reset was run twice, followed by setup, verify and reset; all completed. The
shared Goldpinger Deployment remained available after these cleanup checks.

## Automated and document checks

- 22 definitions, 44 question/solution cards and 176 shell blocks passed content,
  mapping, rendering and syntax checks. Fixture YAML and embedded Python were
  parsed, including Python contained in Kubernetes command arguments.
- 21 regression tests passed. New tests cover controlled manifest differences,
  the HTTP response body, propagation of failed observations, and exclusion of
  terminating consumers from final response checks.
- Both Ansible playbooks passed syntax checks. All 44 Ansible-rendered cards were
  compared with their offline equivalents. All 30 extracted Kubernetes resources
  passed strict Kubernetes 1.35 schemas, with no invalid, errored or skipped
  resources, in addition to live acceptance of the new fixtures by Kubernetes 1.37.
- The Bash runner can read the new questions and solutions offline. The Markdown
  guide and 59-page print edition were regenerated from the definitions; PDF
  pages were rendered and visually reviewed.

## Limits

This validates real Docker and Kubernetes behavior on AMD64, but does not certify
the complete Vagrant/VirtualBox provisioning path or ARM64 execution. The new
storage experiment uses rootful Docker without user namespace remapping. The
network lab does not claim NetworkPolicy enforcement. Warm cached images were
used. Existing labs were covered by regression/rendering checks; their previous
live results remain documented separately. `chaos-theory.pdf` remains an archival
export; the maintained and expanded theory is `chaos-theory.md`.
