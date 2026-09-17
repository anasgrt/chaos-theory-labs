# Chaos Labs VM

This project creates the disposable Ubuntu 24.04 VM required by `chaos-labs.md`, then configures its shared tooling with a separate Ansible run. It installs prerequisites and caches required images; it does **not** create a lab service, a kind cluster, a fault, or an experiment result.

## Prerequisites

- Vagrant 2.4 or later
- VirtualBox 7.1 or later
- Ansible on the macOS host
- Working outbound HTTPS and DNS resolution from the VM while Ansible downloads sources and container images
- At least 16 GB host RAM free for the default 12 GiB VM; use 16 GiB in the VM before Lab 14.

The default box is `bento/ubuntu-24.04` version `202502.21.0`, with catalog update checks disabled. It publishes native `arm64` and `amd64` VirtualBox variants and supplies a 64 GiB virtual disk. The box initially exposes a 30 GiB LVM root volume; the shared Ansible playbook expands it to the available disk capacity before downloading lab fixtures. The default VM has 4 vCPUs and 12 GiB RAM. Set `CHAOS_LABS_CPUS` or `CHAOS_LABS_MEMORY_MB` before first boot to increase them. The Ansible capacity gate verifies the guide's 60 GiB minimum.

## Bring up and configure

One command: `./up.sh` runs `vagrant up`, then `./ansible/run.sh`. The same steps run manually:

1. Create only the VM with `vagrant up --provider=virtualbox`.
2. From the macOS host, run `./ansible/run.sh` to configure it.
3. Open a new VM login with `vagrant ssh`. The new login activates the Docker group membership.
4. Read `~/labs/chaos-labs.md` and begin the desired lab.

`ansible/run.sh` obtains the live SSH host, port, and private key from `vagrant ssh-config`; it does not depend on a fixed forwarded port or a macOS shared folder. Re-run it safely to repair/install missing shared prerequisites. Forward Ansible options to it, for example `./ansible/run.sh --check`.

After the Ansible run succeeds, save `01-tools` with Vagrant before practicing. Use a new snapshot before each session and restore a snapshot rather than trying to recover a lost VM or an unclean fault.

## Tear down

`./down.sh` destroys the VM and its snapshots immediately, without a confirmation prompt. The downloaded box stays cached.

## Run an individual lab

The shared provisioner remains separate from individual labs. From the macOS host, use the numbered lifecycle runner:

1. List the available labs with `./ansible/run-lab.sh list`. The labs follow the chapters kept in `chaos-theory.md` (1–3, 5–6, 10–12); six labs were removed with Chapters 4, 7, 8, 9 and 13, and the remaining 17 labs are numbered 00–16.
2. Prepare one lab with `./ansible/run-lab.sh 04 setup`. The last thing it prints is **YOUR TASK**: the question to answer, the theory you need, the prediction to write down, the steps and the evidence your answer must show.
3. Confirm its safe baseline with `./ansible/run-lab.sh 04 verify`.
4. Reprint the task at any time with `./ansible/run-lab.sh 04 question`. It changes nothing on the VM, unlike re-running `setup`, which resets the fixture.
5. Print the core solution, verification objective and step-by-step practical commands with `./ansible/run-lab.sh 04 solution`.
6. Remove only that lab's automated fixture with `./ansible/run-lab.sh 04 reset`.

Each lab definition has a required `task` block: `question`, `brief`, `predict`, `steps` and `answer_with`. The `brief` holds the theory needed to answer the question: `theory` points from `chaos-theory.md` with chapter references, and `in_this_lab` facts about this fixture's configuration. The question and steps come from that lab's Goal, Prediction and "Done when" in `chaos-labs.md`. The playbook fails early if a lab lacks one. `setup` first runs that lab's scoped reset, then creates only its safe prerequisites; it never executes the intentional fault. `verify` runs executable readiness checks. `solution` prints the guide-aligned solution path, then each lab's `commands` list as plain, pasteable blocks: where to run each block (VM terminal, Mac host, or browser) and the expected evidence. The commands follow the lab's core experiment in `chaos-labs.md`, adapted to the fixture that `setup` already created (for example, the recorded PID files that `reset` uses). Command blocks are tagged `!unsafe` so Ansible does not template Docker/kubectl `{{...}}` formats, and they are rendered to a local text file because Ansible's `debug` output escapes quotes and newlines. The full **Concept**, **Mechanism** and **Question** text is printed before every setup, and the full task card after it, so the learning objective stays with the runnable fixture.

**VS Code YAML support:** `.vscode/settings.json` contains `"yaml.customTags": ["!unsafe scalar"]` so the YAML extension recognizes Ansible's `!unsafe` tag without reporting it as unknown. `scalar` means a single value, including a multiline command string. The tag tells Ansible to preserve that text literally; the VS Code setting only affects editor validation and does not enable command execution or change Ansible's behavior.

Labs are independently addressable but retain the guide's explicit shared-fixture dependencies: Lab 7 creates its own WordPress/MySQL stack on port 8080, which Lab 8's setup stops because its server uses the same port; Lab 9 uses the Lab 8 theory only; Labs 11–13 require Lab 10's `chaos` kind cluster; Lab 14 uses a separate `ha` cluster and should not run alongside `chaos` on the default-memory VM. Run the prerequisite lab's `setup` first and preserve its fixture until dependent labs are complete.

Labs 10 and 14 check resolution of the Docker registry and Kubernetes download endpoints before creating a cluster. If that check fails, repair VM DNS and rerun the setup; no partial cluster is created by that preflight.

## Deliberate boundaries

- `Vagrantfile` only declares the Linux VM, CPU/RAM/disk resources, and disables `/vagrant` sharing. It has no provisioner.
- `ansible/playbook.yml` installs the Lab 0 package set, enables rootful Docker, points default-bridge container DNS at the VM's own resolver (systemd-resolved also listens on the Docker bridge gateway, because VirtualBox's IPv4 NAT resolver can stay silent), raises the inotify limits to kind's documented values (Lab 14's five node containers exceed the defaults), runs `hello-world`, leaves Redis and NGINX stopped, verifies cgroup v2 and available controllers, clones the pinned companion source, installs kind v0.33.0, and caches core lab images.
- A kind cluster is **not** created by Ansible. Labs 10–13 use the `chaos` cluster and Lab 14 creates the separate `ha` cluster; cluster lifecycle is part of the exercises.
- `kubectl` is intentionally not installed until after a kind cluster is created. Run `~/labs/install-kubectl-for-kind.sh chaos` (or `ha`) to install the client version derived from that cluster's control plane and verified with the upstream SHA-256 file.
- The published Goldpinger v3.11.3 tag has no ARM64 manifest. On ARM64, Ansible installs Ubuntu's `docker-buildx` plugin and builds its pinned v3.11.3 source locally under the unchanged `bloomberg/goldpinger:v3.11.3` tag. Labs 10 and 14 load their required, locally cached fixture images into their kind nodes before applying manifests; `~/labs/load-lab-images-into-kind.sh chaos` remains available to load Goldpinger manually. This avoids later per-Pod registry downloads and is safe on AMD64 too.
- Optional BCC tracing tools, Byteman, Prometheus, and PowerfulSeal are not installed because the guide marks them optional and version-dependent.

The VM's lab workspace is `~/labs` on its VM-local root filesystem, not a macOS mount. It contains the guide, provisioning notes, `common.sh`, version record, pinned book source, and Kubernetes client installer. This avoids distorting Docker volumes, `fio` measurements, namespace mounts, or ownership semantics.

## Lab capacity

The default configuration meets the guide's baseline. Before Lab 14, remove the earlier `chaos` kind cluster as instructed and reboot/reload the VM with at least 16 GiB (`CHAOS_LABS_MEMORY_MB=16384`) if the host has capacity.

All workload, fault-injection, and recovery commands remain in the lab guide and run only when you choose to practice that lab.
