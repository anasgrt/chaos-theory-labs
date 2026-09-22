# Theory-first lab refactor

Reviewed all 33 lab definitions, their questions, worked answers and command blocks.
The learning objective remains a controlled comparison: predict, change one variable,
observe the mechanism, recover, and explain the limits of the evidence.

Thirty definitions changed. Learner-facing procedure blocks went from 1,211 to
925 lines (24% fewer), with the largest reductions in the measurement-heavy labs.
This count excludes setup and helper implementations; those still do the necessary work.

## What changed

- The README now starts with the learning workflow and a short suggested path.
- Direct fault and recovery commands stay on the cards. Repeated measurement loops,
  output formatting, timing and fixture copying move into supplied, lab-local
  `exercise.sh` files. The cards explain each helper's purpose and inputs.
- Native `describe`, `logs`, `cat` and EndpointSlice YAML replace incidental filtering
  where they show the required evidence directly. Necessary short selectors remain.
- Lab 12 uses named trials with saved diagnostics and a summary that rejects an
  incomplete run. Lab 13 retains its timestamped node, Lease and container evidence.
- Lab 27 prepares two manifests differing only in the profiling argument. It installs
  them without learner-written `sed`, keeps backups outside the static Pod directory,
  and waits for both API readiness and the requested mirror-Pod argument.
- Labs 24, 25, 27, 30 and 31 distinguish an expired wait or failed read from recovery.
  Secret rotation no longer prints an observed change when none was observed.
- The authoring contract documents how to keep later additions straightforward.
  The setup/reset lifecycle, isolation boundaries and public `lab.sh` interface
  are unchanged.

Labs 03, 06 and 09 retain their existing procedures: their short loops, bounded
filesystem guard and seccomp observation directly support the experiment.

## Accuracy corrections

Lab 23 now distinguishes unfinished requests at SIGTERM from new traffic after
deletion, and explains that preStop shares the grace period, with a small termination
extension. It no longer promises an exact signal time or failure count. See the
[Kubernetes Pod termination flow](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination-flow).

Lab 32 explains the `TYPE/NAME` interpretation of `pods/exec` and the explicit
`--subresource=exec` form, instead of presenting their answers as equivalent queries.
See the [kubectl auth can-i reference](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_auth/kubectl_auth_can-i/).

The review also narrows claims about PID limits, unlabelled namespaces and a
ServiceAccount's tested permissions. Secret propagation time is an observation
to collect, not a fixed expected delay.

## Validation

Completed on 2026-09-21 against a fixed copy of the final source in WSL/Linux:

- `bash scripts/validate.sh`: passed, including all 44 regression tests.
- Content checks: 33 labs, 66 cards and 284 embedded shell blocks; fixture shell,
  Python and YAML syntax; generated-guide freshness.
- Ansible integration: all declared fixture files installed, and all 66 cards
  matched the authoring renderer. Lifecycle routing and identity guards passed.
- Print edition: regenerated all 33 labs in 123 pages, checked extracted text,
  rendered every page and visually reviewed the layouts.
- `git diff --check`: passed. Lab sources matched the tested snapshot.

The repository validation covers content, shell and embedded program syntax,
generated-guide freshness, lifecycle routing, Ansible syntax, identity guards,
fixture installation, card parity and regression tests. Additional helper tests
exercise missing API evidence, empty versus unready endpoints, stale startup
results, deadline misses and waits that must not report success.

These checks do not establish live fault outcomes. The teaching VM was saved and
Docker was unavailable in the WSL validation environment; a complete live run of
all 33 labs was not performed. Timing, runtime and networking observations still
need to be collected on the learner's VM. Expected patterns remain labelled as
expectations throughout the cards and print edition.
