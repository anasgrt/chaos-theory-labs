# Container and Kubernetes labs

Learn one mechanism, change one thing, observe the result, and explain why it happened.
These 27 independent labs teach Linux containers and Kubernetes through small,
controlled experiments: seven container labs and 20 Kubernetes labs.

Provisioning installs **Rancher on a permanent single-node RKE2 cluster** inside
the teaching VM. The experiments retain separate Docker containers and disposable
kind clusters, so a lab can break its API server or DNS without targeting Rancher.
See [Rancher and RKE2 setup](docs/rancher-rke2.md) for installation, browser access,
credentials, verification and the exact limits of this architecture.

Labs are numbered consecutively from 00 through 26; use `./lab.sh list` to see
the available labs. Standalone general Linux and chaos engineering labs have
been retired. The [numbering map](docs/lab-numbering.md) translates historical IDs.
Old IDs are not aliases: before using an existing VM, save results and clean up
fixtures with the old checkout, or use a fresh VM. Renumbering does not migrate
existing VM resources.

Start with a question card: `./lab.sh 00 question`. It contains the theory you need
and the steps to run. Each lab's **Main lesson to learn in this lab** section
distils the central mechanism, key distinction and conclusion into one short paragraph.
Write your explanation, then compare with
`./lab.sh 00 solution`. Answers explain expected behaviour; your measurements may differ.

Commands that express the lesson stay visible: change a timeout, delete a Pod,
set a resource limit, apply a policy, or restore a configuration. Setup supplies
the fixture. Small named helpers handle repeated sampling, timing and output
formatting. Each card explains what its helpers do and what their output means;
you do not need to study their shell code to complete the lab.

Choose a topic you need, or begin with this short path:

| Lab | Learn |
| --- | --- |
| 00 | Container namespaces versus cgroup resource limits |
| 07 | Signal delivery and the container shutdown budget |
| 03 | Pod replacement, disruption budgets and Service selection |
| 04 | Why a health check can disagree with a real caller |
| 09 | Scheduling failures versus runtime memory limits |
| 10 | Diagnose DNS, Service ports and listener addresses separately |
| 11 | Configuration changes and rollout recovery |
| 23 | Startup, readiness and liveness failures |
| 24 | Volume placement, deletion protection and retained data |
| 25 | ResourceQuota and LimitRange admission failures |
| 26 | Secret encryption, missing keys and data recovery |

Use the [learner guide](docs/chaos-labs.md) for all 27 labs, the full topic map and
results tables, or the [print edition](docs/chaos-labs.pdf) for offline study.
[chaos-theory.md](docs/chaos-theory.md) is the broader background reference, with
stable section numbers used by the retained labs; its archived PDF is historical.
Reports in `docs/reviews/` record earlier versions and may mention retired labs;
they do not define the current catalog. See the [simplicity review](docs/reviews/simplicity-review.md)
for the refactor decisions, and the [expansion review](docs/reviews/kubernetes-expansion-review.md)
for the new labs' live results and validation limits.

## One VM, independent labs

Install Bash, Vagrant 2.4+, VirtualBox 7.1+ and Ansible on a Linux or macOS host.
Provisioning and Kubernetes setup need outbound HTTPS and DNS. The lifecycle uses Vagrant and Ansible,
with no custom Python setup or reset program. Ansible and some teaching applications
use Python internally.

```bash
./lab.sh provision       # once: create the VM and install shared tools
./lab.sh platform        # verify RKE2, Rancher and HTTPS
./lab.sh 04 setup        # prepare Lab 04, without running any other lab
./lab.sh ssh             # run the question's procedure inside the VM
./lab.sh 04 reset        # remove only Lab 04's resources and files
./lab.sh 07 setup        # choose any next lab
```

All 27 labs run inside the same Ubuntu VM, named `chaos`. Each setup creates its
own fixture. Each reset stops its own processes and removes its containers,
services, mounts, fault rules and `~/labs/labNN/` workspace as applicable. Shared
tools, cached images and other labs are preserved.

Kubernetes labs each create a named kind cluster inside this VM (`lab03`, `lab04`,
and so on), with a private kubeconfig. Lab 04 does not need Lab 03.
Reset deletes only the selected cluster and
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
| `./lab.sh platform` | Verify the permanent RKE2 API, Rancher deployment and HTTPS |
| `./lab.sh ssh` | Open a shell in the shared VM |
| `./lab.sh status` | Show the shared VM state |
| `./lab.sh stop` | Halt the whole VM, preserving all files |
| `./lab.sh start` | Resume the VM without provisioning again |

Save results before setup or reset removes them. The recovery commands within a
question test recovery; reset cleans up the experiment afterward.

The VM defaults to 24 GiB RAM, 6 vCPUs and a dynamically allocated 64 GiB disk.
Set resources and the host-only IP in [config/platform.yml](config/platform.yml)
before first provisioning; Vagrant and Ansible use the same configuration.
Allow memory for the host as well. Reset finished
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
config/platform.yml          VM resources, Rancher address and verified release pins
labs/
  NN-topic/
    lab.yml                  Theory, question, procedure and lifecycle steps
    files/                   Supporting programs and manifests, when needed
ansible/
  provision.yml              Configure the shared Ubuntu VM once
  platform.yml               Verify the permanent Rancher and RKE2 platform
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
setups create the containers, namespaces and clusters they need.
It configures Docker DNS through the VM resolver, requires cgroup v2 and raises
inotify limits for kind. It installs kind v0.33.0. `kubectl` is installed after
cluster creation using the control plane's version and an upstream checksum.
RKE2 uses its own containerd, bundled Kubernetes client and private kubeconfig.
Use `rke2-kubectl` inside the VM for management; the lab `k` helpers continue to
target their own kind clusters. Lab reset does not uninstall RKE2 or Rancher.

Goldpinger uses the published `bloomberg/goldpinger:3.11.3` image on AMD64 and
ARM64. The image tag has no `v` prefix, unlike its source release tag. Cluster
setups load cached images into their nodes, avoiding per-Pod registry downloads.
The NGINX container image is still required by Lab 06; host NGINX,
Redis and the retired syscall lab's companion source are no longer provisioned.
This source cleanup does not remove fixtures or packages from an existing VM.

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
silently skipped. It checks content and guide freshness, shell routing, all four
playbooks, identity guards and the complete regression suite. Integration tests
install every lab's files into a temporary directory and compare all 54
Ansible-rendered cards with the authoring renderer. Process cleanup checks require
Linux's `/proc` filesystem.
Platform checks exercise real certificate generation and renewal, Ansible templates,
private kubeconfig references and cluster-target guards. They do not boot a VM.

After editing lab definitions, run `python3 scripts/render-labs.py` to refresh the
guide, then validate again. Local checks do not replace live Ubuntu, Docker and
Kubernetes experiments; acceptance steps are in [docs/lab-design.md](docs/lab-design.md).
Current results and the unresolved VirtualBox Kubernetes acceptance failure are
recorded in [the isolation review](docs/reviews/isolation-review.md).
The earlier [procedure review](docs/reviews/procedure-review.md) uses the original lab numbering.
The [simplicity review](docs/reviews/simplicity-review.md) covers the current refactor.

To regenerate the print edition, install ReportLab and DejaVu Sans/Mono fonts,
then run `python3 scripts/render-labs-pdf.py` to update `docs/chaos-labs.pdf`. Use
`--font-dir` if the fonts are outside `/usr/share/fonts/truetype/dejavu`. Render
and inspect the resulting pages before committing the PDF.
