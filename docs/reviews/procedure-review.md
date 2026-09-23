# Experiment and answer review

> Historical review: this report describes an earlier revision. The current catalog
> contains 27 container and Kubernetes labs, renumbered 00 through 26. Lab numbers
> and counts below use the original catalog and are historical evidence, not current
> setup instructions. See [the numbering map](../lab-numbering.md) for retained labs.

The review covers the parts after the theory in all 22 question cards and their
solutions. The theory paragraphs are unchanged.

Each question now follows one sequence: prediction and measurement key, host
verify/SSH commands, numbered procedure steps, recovery, then numbered answer
prompts. Every procedure block names its terminal and immediately states what
to record. Those instructions request observations; expected outcomes remain
in the solution. Each numbered prompt has a matching worked answer. Terminal
solutions also include the exact procedure commands and recording instructions,
followed by expected observations. This retains operational directions such as
when to detach a tracer or switch terminals.

The Markdown guide and print edition follow the same ordering. The PDF keeps
its worked answers at the end; their step names and numbers match the commands
in each question.

## Completeness checks

| Lab | Evidence and sequence checked |
| --- | --- |
| 00 | Tool/image identities, cgroup mode, paths and disk baseline |
| 01 | Separate REJECT, DROP and timed-DROP cases; per-case counters and client exits; guarded firewall recovery check |
| 02 | TERM, explicit KILL and bounded OOM; allocator PID and matching unit/kernel evidence |
| 03 | Individual crashes, start-limit evidence and explicit service recovery |
| 04 | Baseline/contention/quota durations and before/after throttling deltas from the owned active cgroup |
| 05 | Two-shell namespace experiment, owned cgroup observations and explicit return from the sandbox |
| 06 | Bounded shared mount, separate fill/probe/recovery phases and preserved measurements |
| 07 | One/four-exchange baselines, injected timing, per-case baseline subtraction and fault removal |
| 08 | Baseline server, injected syscall error, trace evidence and fresh-process HTTP recovery |
| 09 | Before/after syscall results, denied-call errno and a fresh process outside the filter |
| 10 | Owner chain, eviction/direct deletion, HTTP availability calculation, selector fault and restored Ready Pods |
| 11 | TCP/HTTP readiness comparisons, caller budgets, same-Pod recovery and separate cleanup |
| 12 | Diagnostics for all seven result rows, fresh trial timestamps, error distinction and restored-sample calculation |
| 13 | Cordon versus kubelet loss, Pod/runtime identities, recorded timeline and qualified interval calculations |
| 14 | Quorum, attempted writes, replica/HTTP observations and guarded recovery/readback |
| 15 | Both retry cases, six phase summaries, runner exits and owned-process cleanup |
| 16 | Create, complete, inspect and retain the written experiment plan |
| 17 | Wrapper/exec delivery, unchanged versus reduced stop budget, logs, markers and exit evidence before cleanup |
| 18 | Container replacement, numeric ownership, read-only mount, writable recovery and separate storage cleanup |
| 19 | Placement evidence versus runtime OOM, initial/current UID, prior logs and healthy replacement |
| 20 | Same-client DNS/Service/Pod paths, current endpoint-port polling, loopback comparison and restored paths |
| 21 | ConfigMap and per-consumer observations, stable revision, stalled rollout, undo and separate configuration restoration |

The second review checked that requested answers have corresponding commands,
that variables/functions remain in the correct shell, and that recovery is
observed before evidence is removed. It corrected missing restored-Pod/runtime
observations, missing counter deltas, misleading failure handling and wait
commands whose request timeout was shorter than their stated operation bound.

## Verification scope

The content checker requires complete step instructions and one worked answer
per prompt. Regression checks verify that questions retain every command and
measurement instruction, hide solution-only content, and that terminal
solutions repeat the exact commands. The Ansible integration compares all 44
rendered cards with the authoring renderer.

The full `scripts/validate.sh` run passed all 34 tests without skips from a
copied checkout whose path contains spaces, invoked outside the repository.
It also passed content consistency, shell syntax and Ansible syntax checks.
All 22 labs retain their original theory paragraphs.

The regenerated 86-page PDF was checked for all question prompts, worked
answers, transfer answers and recording instructions. Every page was rendered
and visually inspected, with full-size checks of representative procedures,
long command blocks and solutions. Text bounds checks found no overflow.

The Lab 01 runner tests execute the generated script with isolated command
substitutes and a harmless client. They check case selection, timeout settings,
invalid arguments, failure reporting and cleanup while preserving a foreign
rule. They do not modify the host firewall or run systemd.

These checks do not constitute a new live run of the revised experiments. The
existing [VirtualBox acceptance limitation](isolation-review.md#live-acceptance-limits)
remains; no new live Kubernetes success is claimed.
