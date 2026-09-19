# Chaos theory labs

Twenty-two focused labs connect the mechanisms in [chaos-theory.md](docs/chaos-theory.md)
to observable results. Read [chaos-labs.md](docs/chaos-labs.md), use the [print edition](docs/chaos-labs.pdf), or print a question in
the terminal. Each question includes the relevant theory, measurement definitions,
a prediction, a results table, a procedure and recovery checks. Solutions are separate.

The container and Kubernetes troubleshooting labs use controlled comparisons:

| Lab | Tasks | Matching theory sections |
| --- | --- | --- |
| 10 | Trace ownership; compare eviction with direct deletion; break and restore Service selection | §§10.5.1–10.5.2 |
| 11 | Compare TCP and HTTP readiness across caller budgets; observe endpoint exclusion and recovery without restarts | §§10.5.3–10.5.4 |
| 12 | Diagnose delayed, unschedulable and incorrectly selected workloads; calculate a restored startup sample SLI | §§11.4.1–11.4.3 |
| 13 | Compare cordon with kubelet loss using placement, Lease, taint and runtime evidence | §§12.3.1–12.3.2 |
| 14 | Compare quorum, configuration writes, replica convergence and HTTP; resolve uncertain writes after recovery | §§12.3.3–12.3.4 |
| 17 | Compare signal delivery through a wrapper and exec, then reduce the shutdown budget | §§5.13.1–5.13.2 |
| 18 | Replace a container; distinguish numeric ownership errors from read-only mounts | §§5.13.3–5.13.4 |
| 19 | Distinguish unschedulable CPU requests from runtime OOM and restart backoff | §§10.6.1–10.6.2 |
| 20 | Isolate DNS, Service targetPort and loopback-only listener failures | §§10.7.1–10.7.2 |
| 21 | Trace ConfigMap consumption; diagnose a stalled rollout; restore template and configuration separately | §§10.8.1–10.8.2 |

Use `docs/chaos-theory.md` as the maintained theory source. `docs/archive/chaos-theory.pdf` is an older
reference export and does not include these additions. The lab PDF is regenerated
from the same definitions as the terminal cards. See [the Kubernetes review](docs/reviews/kubernetes-review.md)
for the original expansion, and [the container and Kubernetes review](docs/reviews/troubleshooting-review.md)
for the additional exercises and validation limits.

## One VM, independent labs

Install Bash, Vagrant 2.4+, VirtualBox 7.1+ and Ansible on a Linux or macOS host.
Provisioning and Kubernetes setup need outbound HTTPS and DNS. The lifecycle uses Vagrant and Ansible,
with no custom Python setup or reset program. Ansible and some teaching applications
use Python internally.

```bash
./lab.sh provision       # once: create the VM and install shared tools
./lab.sh 11 setup        # prepare Lab 11, without running any other lab
./lab.sh ssh             # run the question's procedure inside the VM
./lab.sh 11 reset        # remove only Lab 11's resources and files
./lab.sh 03 setup        # choose any next lab
```

All 22 labs run inside the same Ubuntu VM, named `chaos`. Each setup creates its
own fixture. Each reset stops its own processes and removes its containers,
services, mounts, fault rules and `~/labs/labNN/` workspace as applicable. Shared
tools, cached images, the companion source and other labs are preserved.

Kubernetes labs each create a named kind cluster inside this VM (`lab10`, `lab11`,
and so on), with a private kubeconfig. Lab 11 does not need Lab 10. Lab 14 does not
require deleting another cluster. Reset deletes only the selected cluster and
works when its Kubernetes API is broken; the VM, SSH and Docker must still work.
The first Kubernetes setup downloads a large node image; cluster creation allows
up to 30 minutes for that initial work. Later setups reuse the image cache.

| Command | Effect |
| --- | --- |
| `./lab.sh NN setup` | Clear that lab's previous fixture, prepare it and verify readiness |
| `./lab.sh NN verify` | Check that lab's starting state |
| `./lab.sh NN reset` | Remove that lab's resources and workspace |
| `./lab.sh NN question` | Read its theory and procedure without a VM |
| `./lab.sh NN solution` | Read its explanation and expected patterns without a VM |
| `./lab.sh list` | List all labs |
| `./lab.sh ssh` | Open a shell in the shared VM |
| `./lab.sh status` | Show the shared VM state |
| `./lab.sh stop` | Halt the whole VM, preserving all files |
| `./lab.sh start` | Resume the VM without provisioning again |

Save results before setup or reset removes them. Lab 16 preserves its written
card on repeated setup; reset still removes it. The recovery commands within a
question test recovery; reset cleans up the experiment afterward.

The VM has 16 GiB RAM, 4 vCPUs and a dynamically allocated 64 GiB disk, including
enough configured RAM for Lab 14. Allow memory for the host as well. Reset finished
labs to release their resources; keeping many Kubernetes clusters running can
exhaust the same VM. Resource contention is shared even though setup/reset targets
are separate. No lab sequence or per-lab memory reload is required.

The pinned box is `bento/ubuntu-24.04` version `202502.21.0`. Files live on the guest
filesystem; no host folder is shared. Kind nodes are containers, not additional
VMs or independent physical machines. Ansible checks the inventory name and guest
hostname before changing lab resources.

## Repository structure

```text
lab.sh                       Public command for every lab action
Vagrantfile                  One shared VM for all labs
labs/
  NN-topic/
    lab.yml                  Theory, question, procedure and lifecycle steps
    files/                   Supporting programs and manifests, when needed
ansible/
  provision.yml              Configure the shared Ubuntu VM once
  labs.yml                   Set up, verify or reset the selected fixture
  cards.yml                  Read questions and solutions without a VM
  tasks/                     Shared identity, file-copy and cluster tasks
  files/                     Shared guest helpers and cluster manifests
  templates/                 Question and solution templates
  inventory/                 Empty default inventory; runtime targets one VM
scripts/
  validate.sh                Run all local maintainer checks
  render-labs*.py             Generate the learner guide and print edition
  check-labs.py              Validate content, embedded code and guide freshness
  lab_content.py             Shared authoring loader and card renderer
  labs.py                    Read cards with the authoring renderer
  run-ansible.sh, lib/        Internal lifecycle shell helpers
tests/                       Regression tests and Ansible integration checks
docs/
  chaos-theory.md             Maintained theory reference
  chaos-labs.md               Generated learner guide
  chaos-labs.pdf              Generated print edition
  lab-design.md              Content contract and authoring instructions
  reviews/                   Review reports and validation evidence
  archive/                   Historical theory PDF
```

Edit a lab in its own folder; the guide and print edition are generated from those
definitions. File names under `files:` are relative to that lab's `files/` folder.
Ansible installs them into the same `~/labs/labNN/` guest paths used by the exercises.
Keep files in `ansible/files/` only when they are shared infrastructure.

The public entry point is now `./lab.sh`. It replaces `ansible/run-lab.sh`,
`up.sh` and `down.sh`; use `./lab.sh NN setup` and `./lab.sh NN reset`.
The current commands use the single `chaos` VM; old per-lab VMs are not deleted automatically.
Local `tmp/`, `output/` and `.vagrant/` directories hold ignored diagnostics,
rendering output and VM state; they are not lab source files.

The provisioner installs common tools and caches the required images; individual
setups create the services and clusters. It leaves Redis and system NGINX stopped.
It configures Docker DNS through the VM resolver, requires cgroup v2 and raises
inotify limits for kind. It installs kind v0.33.0. `kubectl` is installed after
cluster creation using the control plane's version and an upstream checksum.

Goldpinger uses the published `bloomberg/goldpinger:3.11.3` image on AMD64 and
ARM64. The image tag has no `v` prefix, unlike its source release tag. Cluster
setups load cached images into their nodes, avoiding per-Pod registry downloads. The companion
book source is pinned at `3e3ee64db71f51a5e9f79af8562dd4aa913a0e71` for Lab 08.

`scripts/run-ansible.sh NN` obtains connection details for the shared `chaos` VM from Vagrant.
Use `./lab.sh provision` once, then `./lab.sh NN setup` to prepare a lab.
Command blocks use `!unsafe` to preserve literal Docker and kubectl `{{...}}`
expressions. For a YAML editor, register the custom tag `!unsafe scalar`.

## Validate changes

These optional authoring tools use Python; they are not used by setup or reset.
On Linux or WSL, install Ansible, Bash, jq and `requirements-dev.txt`, then run:

```bash
python3 -m pip install -r requirements-dev.txt
bash scripts/validate.sh
```

The validation command works from any working directory and does not change the
VM or generated documents. It requires Ansible so integration checks cannot be
silently skipped. It checks content and guide freshness, shell routing, all three
playbooks, identity guards and the complete regression suite. Integration tests
install every lab's files into a temporary directory and compare all 44
Ansible-rendered cards with the authoring renderer. Process cleanup checks require
Linux's `/proc` filesystem.

After editing lab definitions, run `python3 scripts/render-labs.py` to refresh the
guide, then validate again. Local checks do not replace live Ubuntu, Docker and
Kubernetes experiments; acceptance steps are in [docs/lab-design.md](docs/lab-design.md).
Current results and the unresolved VirtualBox Kubernetes acceptance failure are
recorded in [the isolation review](docs/reviews/isolation-review.md).

To regenerate the print edition, install ReportLab and DejaVu Sans/Mono fonts,
then run `python3 scripts/render-labs-pdf.py` to update `docs/chaos-labs.pdf`. Use
`--font-dir` if the fonts are outside `/usr/share/fonts/truetype/dejavu`. Render
and inspect the resulting pages before committing the PDF.
