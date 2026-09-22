# Kubernetes expansion and main-lesson review

Reviewed on 2026-09-21. This extends the earlier
[simplicity review](simplicity-review.md) with Labs 33-36 and the main-lesson
sections for all 37 labs.

## Learning design

Every lab now has a brief "Main lesson to learn in this lab" paragraph, following
the theory in the question, learner guide and PDF, and opening the solution card.
The paragraphs retain the mechanism, its important distinction and the conclusion;
they range from 55 to 65 words. A comparison against the previous revision confirmed
that the original 33 labs retain their questions, answers, commands and lifecycle.
Theory wording was clarified for process reaping, admission webhook failures,
kubelet Secret access and NetworkPolicy scope.

The four additions keep the existing independent setup/reset interface. Learners
change the fault and recovery settings directly; small named helpers collect
evidence or wait for an observed state. Each helper's purpose and failure behavior
are explained on the card.

| Lab | Comparison and retained lesson |
| --- | --- |
| 33 | Readiness withdrawal, a repairable liveness failure, and removal of startup protection; distinguish container identity from Pod identity. |
| 34 | Delayed claim binding, contradictory placement, deletion protection and retained data; distinguish the claim, volume object and backing directory. |
| 35 | Missing requests, per-container maximum and aggregate quota; distinguish admission rejection from scheduling and runtime failure. |
| 36 | Existing plaintext, encrypted writes, explicit rewrite and missing-key recovery; distinguish API access, stored bytes and key availability. |

## Source review

The theory reference links the primary documentation beside each explanation:
[probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/),
[persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/),
[resource quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/),
[LimitRange](https://kubernetes.io/docs/concepts/policy/limit-range/) and
[encryption at rest](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/).
The probe design discussion also cites a
[CNCF engineering article](https://www.cncf.io/blog/2022/02/17/principles-for-designing-and-deploying-scalable-applications-on-kubernetes/).
Quota security context links the
[NSA/CISA hardening guidance announcement](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-release-kubernetes-hardening-guidance/).

## Repository and document validation

`bash scripts/validate.sh` passed in a Linux/WSL source snapshot:

- 53 regression tests, including nine targeted tests for the new comparisons and
  encryption evidence handling.
- 37 lab definitions, 74 question/solution cards and 321 embedded shell blocks;
  Python/YAML and fixture syntax, plus generated-guide freshness.
- Lifecycle routing, Ansible playbook syntax, identity guards, fixture installation,
  card rendering parity and reset isolation.

Before publishing, the remote Lab 19 fix (`b420ebc`) was incorporated: its readiness
probe changes and bounded log output are preserved. The guide and PDF were then
regenerated from the combined source, with content, fixture syntax and card tests
rerun for that integration.

The rebuilt print edition has 144 pages. Text extraction confirmed every complete
main-lesson paragraph. All pages were rendered for visual review; the final topic
index fits on one page, and image comparisons confirmed that tightening its spacing
did not change the following page bodies. The new lab questions and solutions were
reviewed alongside their source definitions.

## Live evidence

All four new labs completed setup, baseline verification and their learner command
blocks on Docker-hosted kind clusters using Kubernetes v1.37.0. The acceptance
runner read the actual `lab.yml` setup, verify and command blocks. Expected failing
commands were checked against their errors and subsequent evidence, rather than
treating the script's final exit status alone as a pass.

| Lab | Observed result |
| --- | --- |
| 33 | Readiness changed without changing the Pod or container identity. The progress fault restarted the container within the same Pod. Removing startup protection caused restarts before initialization completed; restoring it returned HTTP 200 with zero restarts in the replacement Pod. |
| 34 | The unconsumed claim remained Pending; the conflicting consumer remained unscheduled. Replacement preserved the claim and marker. Claim deletion showed PVC protection, then a Released PV with the old claim UID. A new claim recovered the original marker from the retained directory. |
| 35 | Missing requests, the excessive memory limit and exhausted CPU-request quota produced separate Forbidden errors and no corresponding Pod. Reducing quota preserved both existing UIDs and readiness. Freeing allowance admitted the retried Pod; recovery left only the original baseline workload and no temporary LimitRange. |
| 36 | Enabling encryption left the old record byte-for-byte unchanged until its rewrite. New and rewritten records acquired the key1 prefix. With key2 installed, the API became live, readiness failed and the Secret read returned a missing-key error. Restoring key1 recovered both API values. The fresh record's ciphertext was identical before the fault, during it and after recovery. |

Private-cluster cleanup used the repository's Ansible reset path. Local evidence
and logs were retained under ignored `tmp/expansion-*` paths; generated lab keys
are not repository content.

## Validation limits

This was live Kubernetes acceptance of the four additions, not a fresh live run of
all 37 labs. The Docker controller supplied the test clusters and internal
kubeconfigs because the Windows VirtualBox teaching VM was too slow to complete
the full provisioning path reliably. These runs therefore do not establish a
complete Vagrant/VirtualBox provisioning pass. Shared lifecycle behavior was
covered separately by repository tests.

Timing remains environment-dependent. A local retained directory is not replicated
storage, namespace quotas do not reserve node capacity, and the disposable local
encryption-key fixture is not a production key-management design. The cards make
these boundaries explicit and label observations as expected patterns rather than
measurements from the learner's VM.
