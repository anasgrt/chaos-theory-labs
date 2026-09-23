# Single-VM lifecycle review

> Historical review: this report describes an earlier revision. The current catalog
> contains 27 container and Kubernetes labs, renumbered 00 through 26. Lab numbers
> and counts below use the original catalog and are historical evidence, not current
> setup instructions. See [the numbering map](../lab-numbering.md) for retained labs.

The current design replaces the earlier per-lab VM implementation. Provision one
Vagrant VM (`chaos`, hostname `chaos-labs`) and run all lab fixtures inside it.
There is no required lab order.

## Resource ownership

- Each lab owns `~/labs/labNN/`, including its results and private configuration.
- Systemd units and Docker containers use `ce-labNN` names. Reset stops only those
  units/containers before deleting files. Lab 01 owns Redis on 6381; Lab 03 owns
  its NGINX instance. Lab 15's runner and children belong to its own systemd unit.
- Each Kubernetes lab owns cluster `labNN` and `~/labs/labNN/kubeconfig`.
  Lab 11 creates its own Goldpinger fixture. Reset uses named kind deletion and
  needs no healthy Kubernetes API. This follows kind's [named-cluster lifecycle](https://kind.sigs.k8s.io/docs/user/quick-start/#deleting-a-cluster).
- Reset preserves the VM, shared packages, image caches, companion source, other
  labs and the shared Docker network. The VM, SSH and Docker must remain usable.
- Setup runs the same scoped cleanup before rebuilding its fixture. Lab 16 keeps
  its written card on repeated setup; explicit reset removes it.

The lifecycle and card reader use Bash, Vagrant and Ansible. Python is used by
Ansible, some teaching workloads and optional authoring/tests, not a custom
setup/reset controller. VM capacity and kernel resources remain shared; independent
cleanup does not guarantee performance isolation.

## Verification

The wrapper tests cover all 22 labs, one shared inventory/SSH target, no VM
creation or destruction during lab setup/reset, provision-once routing, invalid
IDs, duplicate definitions, errors, offline cards and paths containing spaces.

All 29 regression tests pass. The real Ansible integration renders all 44 cards
and installs all 19 supporting files. A separate reset integration uses isolated filesystem fixtures and fake
Docker/kind commands. It checks named cluster deletion with kubectl unavailable,
reset before setup, repeated reset, foreign-unit rejection, container/volume
ownership, preservation of another lab and shared files, failure propagation and
Lab 16's setup/reset distinction. Fake runtime tests do not certify live clusters.
Two real-process checks also prove that stale PID files cannot kill another lab's
server or port-forward.

A concurrent rerun on the Windows-mounted filesystem hit the 600/300-second
Ansible integration limits. The unchanged source and Ansible runtime were copied
to Linux storage: all 29 tests passed in 115 seconds, followed by content and
lifecycle checks. No test timeout or assertion was relaxed.

The final maintainer entry point, `bash scripts/validate.sh`, also passed from an
unrelated working directory with the checkout in a path containing spaces. It
checked content and guide freshness, shell routing, all three playbooks and the
identity guards; all 29 regression tests passed in 81 seconds without skips,
including the real Ansible card, fixture and reset integrations.
The hostname rejection test now uses a temporary controlled hostname rather
than assuming the controller has a different name from the guest. Its focused
Ansible rerun passed with both expected rejections and fixture cleanup verified.

Vagrant and Ansible syntax checks, identity rejection checks, content/embedded
program validation and document-link checks cover the reorganized tree. The guide
and 59-page PDF use the same lab definitions; all rendered PDF pages were reviewed.

Strict Kubernetes 1.37.0 schema validation passes for all 24 resources in 14
manifest files. A separate helper check verifies checksum validation, atomic
kubectl installation and reuse of an already installed matching client. Updating
the client therefore does not truncate a binary another lab is executing.

## Live acceptance limits

Earlier tests of the previous architecture passed Lab 17's signal experiment and
some Docker-hosted Kubernetes exercises. They do not validate this single-VM
refactor. Previous VirtualBox tests also encountered kernel stalls and kind node
startup/control-plane timeouts; their root cause was not established.

The shared VM provisioned successfully: Ansible reported 51 successful tasks and
zero failures. Docker, registry DNS, cgroup v2, shared tools and the provisioning
marker were checked in the guest.

Setup, baseline verification and reset passed for all 14 non-Kubernetes labs
(00–09 and 15–18), with zero Ansible failures. Final cleanup removed the test
workspaces and lab containers. The live isolation checks also passed for dedicated
Redis cleanup (including its runner and firewall rules), a running service unit, container/volume cleanup,
the retry experiment and repeated design-card setup. Throughout these checks,
Lab 03's HTTP service, marker file and the system NGINX configuration were
preserved. Lab 15's retry experiment recorded 20/20 successful baseline and
recovery requests; under the injected delay, 40 client requests caused 80 backend
requests with zero client successes.

Kubernetes acceptance is still blocked. Lab 19's first setup reached the old
10-minute outer limit during initial node-image preparation. The outer limit is
now 30 minutes, and the retry downloaded the image successfully. It then failed
during node startup, before kubeadm or the lab workload ran:

```text
could not find a log line that matches
"Reached target .*Multi-User System.*|detected cgroup v1"
```

A diagnostic run retained the four nodes. Its control-plane container started at
02:46:11 UTC and reached `Multi-User System` at 02:47:22 UTC, approximately 71
seconds later. Kind v0.33.0 has a separate, fixed [30-second node boot-log
deadline](https://github.com/kubernetes-sigs/kind/blob/v0.33.0/pkg/cluster/internal/providers/docker/provision.go#L410-L419).
Increasing `--wait` or the outer shell timeout does not change that deadline.
The cause of the slow node boot has not been established. Do not interpret the
schema, mock lifecycle or prior Docker-hosted tests as successful live Kubernetes
acceptance on this VirtualBox VM. The planned eight-lab Kubernetes setup sequence
stopped at Lab 19; the two-cluster preservation check did not run.

A final retry ran after the non-Kubernetes test runner and its fixtures were
removed. Its recorded wall time jumped from 02:55 to 06:32 UTC; the command
returned 124 while the node containers were still in `Created` state. This
interrupted run does not establish whether concurrent test load contributed to
the earlier boot delay. No further successful Kubernetes setup is claimed.

The final review also checked the VirtualBox host logs. They report Hyper-V/NEM
execution, including `Snail execution mode`, and 9.3 GiB of available host RAM
when starting the 16 GiB guest. Oracle documents [poor performance when VirtualBox
and Hyper-V share a host](https://docs.oracle.com/en/virtualization/virtualbox/7.1/user/KnownIssues.html).
The interrupted run includes disk operations pending for about 13,000 seconds
and a matching loss of the guest heartbeat. These observations support a host
performance problem; they do not establish the cause of the initial node delay.

A fresh cold boot with the WSL test controller stopped also failed to reach SSH
before any lab setup ran; the guest console showed a kernel stack trace and the
VirtualBox log recorded a large clock catch-up delay. This retry therefore could
not validate Kubernetes. Host virtualization and security settings were not changed.

Reset of the retained, incomplete Lab 19 cluster passed through the actual Ansible
playbook: all four nodes and its workspace were removed without a Kubernetes API.
Lab 03 still served HTTP, retained its marker and left the system NGINX
configuration unchanged. The Vagrant VM ID remained unchanged.

Final Ansible cleanup also removed the nodes left by the interrupted retry.
The guest audit found no lab workspaces, lab containers, active lab units, lab
mounts or Lab 01 firewall rules. Shared provisioning, helpers and companion source
remained. The temporary acceptance controller and its SSH key were removed.
Live Kubernetes acceptance and the two-cluster preservation check remain open
on a host where the provisioned VM boots reliably.
