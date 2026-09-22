# Container and Kubernetes security labs review

Reviewed 20 September 2026. This records the design, measurements and validation
limits for Labs 26–29, which extend the container and Kubernetes path into
security. Earlier lab numbers, procedures and theory sections are unchanged.

## Why these three

Labs 05, 06, 09 and 18 already cover namespaces, capabilities, seccomp and
storage ownership at the container layer, but nothing in the path asked what
authority a workload actually holds, how the cluster's own configuration
compares with a published baseline, what a cluster refuses to run, or what a
compromised Pod can reach. Each lab answers one of those questions with
measurements rather than assertions, and each ends by restoring its starting
state.

## Alignment

| Lab | Main theory | Question-card preparation | Required comparison |
| --- | --- | --- | --- |
| 26 | §§5.15.1–5.15.2 | Capability bitmasks, `NoNewPrivs`, seccomp modes, PID namespace, device exposure, read-only roots | Default; `--pid=host`; `--privileged`; hardened |
| 27 | §§12.6.1–12.6.2 | What a benchmark is, where each control's setting lives, effective versus on-disk configuration, restart cost | Baseline scan; file mode changed and restored; API server flag added and reverted; cluster-admin binding added and removed |
| 28 | §§12.5.1–12.5.2 | Levels, modes, namespace labels, admission timing, controller-surfaced rejection | Unlabelled; relabelled while running; recreated under baseline; plain and hardened under restricted; plain under warn; restored |
| 29 | §§10.11.1–10.11.2 | Projected token contents, JWT subject and expiry, authentication versus authorization, namespaced Roles | Default account; Role and RoleBinding; another namespace; no token; binding removed |

Each card teaches its mechanism before any command, states the fixture's actual
values, explains every measurement including failure evidence, and asks for a
prediction, recorded observations and a transfer answer.

## Live results

Executed on a macOS review host: Docker 29.8 with cgroup v2, and kind v0.33.0
clusters running Kubernetes v1.37.0 on ARM64 using the repository's own
four-node `kind.yaml`. Each lab ran its real setup, verify, full procedure and
verify again.

- **26.** Default: `CapEff=00000000a80425fb`, `Seccomp=2`, `NoNewPrivs=0`, one
  visible PID, 15 device entries, writable root, chown allowed. `--pid=host`:
  identical capabilities and devices, but 255 visible PIDs and the VM's init as
  PID 1. `--privileged`: `CapEff=000001ffffffffff`, **`Seccomp=0`**, 169 device
  entries including the host block devices. Hardened: uid 10001,
  `CapEff=0000000000000000`, `NoNewPrivs=1`, `EROFS` on `/`, writable `/tmp`,
  chown refused with `EPERM`. `docker inspect` agreed with each measurement.
- **27.** The baseline scan of an untouched cluster returned four passes and two
  failures: `1.2.1` and `1.2.21` are unset, so the permissive defaults apply,
  while both file-permission controls, the kubelet control and the RBAC control
  passed. `chmod 644` on `admin.conf` moved only `1.1.13`, whose observed value
  became `644 root:root`, and restoring `600` returned it to PASS. Adding
  `--profiling=false` to the static Pod manifest restarted the API server; the
  control first reported PASS **48 seconds** later, and reverting the flag
  returned it to FAIL with all four nodes present. Binding `cluster-admin` to a
  ServiceAccount failed `5.1.1` naming `ServiceAccount/audit-demo`, and removing
  it restored PASS. The final scan was byte-identical to the baseline.
- **28.** In the unlabelled namespace the privileged Pod ran and listed the
  node's `kubelet`, `containerd`, `containerd-shim` and `systemd`, with
  `/sbin/init` as PID 1. Labelling the namespace `enforce=baseline` returned
  `Warning: existing pods ... violate the new PodSecurity enforce level` and left
  the Pod `Running`; recreating it was refused, naming `host namespaces
  (hostPID=true)` and `privileged`. Under `restricted` the plain Pod was refused
  with four named requirements, while the hardened Pod was admitted and reported
  `uid 10001 capeff 0000000000000000 nonewprivs 1 seccomp 2`. With `warn` the
  same violations came back as a warning followed by `pod/plain created`.
- **29.** The default account presented
  `system:serviceaccount:ce-lab29:default` with a future expiry and received
  `403` in both namespaces. After the Role and RoleBinding the same run returned
  `200 items=2` for its own namespace and `403` for `kube-system`, and
  `auth can-i` answered `yes` then `no` with a nonzero exit. The Pod with
  `automountServiceAccountToken: false` had no credential directory, fell back to
  the `default` namespace in its request and was refused as `system:anonymous`.
  Deleting the RoleBinding restored the original `403`.

## Defects found by these runs, and fixed

1. **`docker cp` cannot write into a read-only container.** Lab 26 originally
   followed Lab 17's create/copy/start pattern, which fails with
   `container rootfs is marked read-only`. The program is now mounted read-only
   from the workspace, which works identically for all four configurations.
2. **Lab 28 ended in a state its own `verify` rejected.** The procedure now
   demonstrates restricted enforcement, then removes the hardened Pod and the
   namespace label, so `verify` passes before and after and the comparison can be
   repeated.
3. **A flaky verification idiom.** `... | tee /dev/stderr | grep -q ...` returns
   141 when `grep` exits before `tee` finishes writing, which made
   `./lab.sh 29 verify` fail intermittently under `pipefail`. Labs 23, 24 and 29
   now capture the output into a variable, print it and then match it; the
   replacement was run 30 times locally and three times per lab against live
   clusters without a failure.
4. **A misleading exit status.** Lab 29 reported the exit code of `head` rather
   than of the listing it was checking; the step now tests for the credential
   directory directly.

## Automated and document checks

- 30 definitions, 60 question/solution cards and 258 shell blocks pass
  `scripts/check-labs.py`, including the rule that a card may only name a fixture
  the lab ships or creates.
- `tests/test-lifecycle.sh` passes with its lab loop extended to 00–29.
- The reset integration covers clusters `lab27`, `lab28` and `lab29`; Lab 26 is a
  Docker lab and removes only `ce-lab26-*` containers.
- `bash scripts/validate.sh` passes in a Debian Linux container: content checks,
  lifecycle routing, three playbook syntax checks, the identity playbook and all
  regression tests.

## Not yet validated

- **The Vagrant VM path and AMD64.** As with Labs 22–25, these runs used a
  different Docker engine and architecture from the teaching VM. Lab 26's
  host-visibility and device output will name that VM's own init and disks.
- **Print edition.** `docs/chaos-labs.pdf` still contains 22 labs.
- **Scope of the security claims.** Lab 26 measures boundaries and does not
  attempt an escape. Lab 27 checks six named controls, which is a demonstration
  of how a benchmark is read, not a complete CIS assessment, and it makes no
  judgement about whether each control suits a given cluster. Lab 28 exercises Pod Security admission only, not image
  scanning, network policy or runtime detection, and kind nodes are containers in
  one VM, so "the node" is a container. Lab 29 covers ServiceAccount identity and
  namespaced RBAC; it does not cover ClusterRoles in use, impersonation beyond
  `auth can-i --as`, or external identity providers.
