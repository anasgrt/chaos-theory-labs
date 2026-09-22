# Question theory review

> Historical review: this report describes an earlier revision. The current catalog
> contains 27 container and Kubernetes labs, renumbered 00 through 26. Lab numbers
> and counts below use the original catalog and are historical evidence, not current
> setup instructions. See [the numbering map](../lab-numbering.md) for retained labs.

Historical teaching-content review. For the current single-VM lifecycle, see
[isolation-review.md](isolation-review.md). Shared-cluster setup notes below are superseded.

Reviewed 19 September 2026. The learner-facing review is `task.brief.theory` plus
`in_this_lab` and `readings`, rendered before predictions and commands. There is
no separate theory source inside the playbook; definitions and shared templates
supply its content.

## Review standard

For every lab, read the question, prediction, evidence table, procedure, answer
requirements and transfer question against the theory shown on that same card.
Then compare its claims with the fixture and measurement implementation. A card
passes when the learner has the mechanism, configured values, measurement rules
and reasoning needed to interpret their own observations without reading the
solution. Basic shell use is assumed; undocumented specialist facts are not.

This is a content audit, not a claim that a word-count or keyword test can prove
teaching quality. Explanations retained below already met the standard; changes
address specific missing rules or misleading statements.

## Coverage of all 22 cards

| Lab | Reasoning the question requires | Review outcome |
| --- | --- | --- |
| 00 | Baseline validity, blast radius, version evidence and recovery point; tool success versus service health | Sufficient; retained |
| 01 | Returned errors versus blocked calls, REJECT/DROP, socket timeouts versus watchdog, multiple attempts | Sufficient; retained |
| 02 | Signal status versus cause, cgroup memory versus VM memory, matching unit/kernel evidence | Sufficient; retained |
| 03 | Restart request versus permission to start, burst allowance, backend versus proxy health | Sufficient; retained |
| 04 | Fixed work, CPU contention, quota enforcement and timing comparisons | Added explicit mean/range calculation |
| 05 | Filesystem/PID views versus resource limits; configuration versus current enforcement | Added quota units, worked conversion and counter deltas |
| 06 | Shared mount capacity, write errors, container versus data lifetime | Explained why the later df can hide dd failure in the container exit status |
| 07 | Per-reply delay, sequential waits, baseline subtraction and persistent qdisc state | Corrected timer boundary; taught overlapping parallel waits for the transfer question |
| 08 | Response before close, application error handling, later availability and injection limits | Explained skipped syscalls versus real close side effects and descriptor reuse |
| 09 | Syscall result/errno versus process exit, filter inheritance and lifetime | Sufficient; retained |
| 10 | Ownership, asynchronous replacement, PDB scope, routing and sampled availability | Defined shared failure domains for the node-loss transfer question |
| 11 | Caller budgets versus probe budgets, endpoint eligibility, freshness and restarts | Explained why dependency-sensitive liveness can reduce capacity without fixing the dependency |
| 12 | Timed startup stages, valid misses versus checker errors, diagnostic freshness and sample fraction | Taught Always/cache semantics and why restart does not change the fault settings |
| 13 | Cordon versus lost supervision, heartbeat/taint delays, Pod identity versus runtime execution | Sufficient; retained |
| 14 | Majority, membership, leader identity, write/convergence/HTTP separation and unknown write outcomes | Defined floor, failure-tolerance arithmetic and idempotent restoration |
| 15 | Original requests versus attempts, retry multiplication and useful work | Defined HTTP 503 before using it as the controlled failure |
| 16 | Measurable hypothesis, control, fault confirmation, stop/recovery and limits | Sufficient; retained |
| 17 | PID 1 delivery, exec, shutdown grace, receipt versus completion and kill attribution | Made signal numbers and the meaning of 137 self-contained |
| 18 | Layer versus volume lifetime, numeric identity, directory permissions and mount read-only enforcement | Sufficient; retained |
| 19 | Scheduling requests versus runtime limits, prior termination, restarts and UID-specific evidence | Defined the memory unit used in the manifest |
| 20 | DNS, Service port translation, endpoint selection and listener reachability | Defined the selector/EndpointSlice relationship on this card |
| 21 | Environment freshness, revisions, readiness versus availability, stall and separate rollback targets | Explained minReadySeconds and the two-available-replica strategy precisely |

The updated main theory also explains the close-injection limitation and defines
idempotent restoration. Existing main-theory sections already covered the other
mechanisms; their missing explanations were brought into the standalone cards.

## Playbook output defect

The direct-playbook fallback previously printed a shortened debug list. It
omitted prerequisites, experiment context, the result table, recovery guidance
and the transfer question. Printing the raw `commands` list also exposed its
solution-only `expect` fields.

Both fallback views now use the same question/solution templates as offline
reading and the normal runner. The question includes the complete theory and
procedure but excludes expected-result notes. Ansible's default callback can
still escape newlines; `lab.sh NN question` remains the plain-text interface.

## Verification

- All 22 definitions, 44 cards and 176 shell blocks passed the content checker.
- All 22 regression tests passed. The added test checks that teaching content is
  retained and solution-only fields are excluded for every question.
- Both playbooks passed Ansible syntax checks. All 44 Ansible-generated cards
  were compared with offline rendering.
- The actual playbook's fallback question and solution were exercised for Labs
  08 and 21 on localhost, without a VM or fault injection, and matched the shared
  renderer. This includes literal shell, Docker and Kubernetes expressions.
- The Markdown and PDF editions were regenerated and the PDF was rendered for
  visual review. Existing runtime procedures and fixtures were not changed in
  this review, so their prior live results remain the applicable runtime evidence.

Source checks used the Linux manuals for [strace](https://man7.org/linux/man-pages/man1/strace.1.html)
and [close](https://man7.org/linux/man-pages/man2/close.2.html), and Kubernetes
documentation for [image caching](https://kubernetes.io/docs/concepts/containers/images/)
and [probe behavior](https://kubernetes.io/docs/concepts/workloads/pods/probes/).
