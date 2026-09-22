# Rancher and RKE2 in the teaching VM

`./lab.sh provision` installs a permanent single-node RKE2 server and runs Rancher
on it through Helm. It also installs Docker and kind for the 27 existing labs.
The management cluster is not a target for destructive experiments.

| Component | Configuration |
| --- | --- |
| VM | Ubuntu 24.04, 24 GiB RAM, 6 CPUs, 64 GiB disk |
| Management network | Host-only address `192.168.56.10`; NAT supplies outbound access |
| Rancher URL | `https://rancher.chaos.test` |
| RKE2 | `v1.35.8+rke2r1`, Canal, Traefik, bundled containerd |
| Rancher | `2.15.1`, one replica, strict agent TLS |
| Helm | `v3.21.4` |
| Management Pods / Services | `10.42.0.0/16` / `10.43.0.0/16` |
| Management client | `rke2-kubectl`, using `~/.kube/rke2.yaml` and context `rke2-management` |
| Lab clients | Per-lab kubeconfigs and `kind-labNN` contexts |

VM resources, the platform address, version pins and release checksums are in
[config/platform.yml](../config/platform.yml). Vagrant and Ansible read that file.
Choose a free host-only address before provisioning; avoid your LAN, VPN, Docker
and Kubernetes networks. VirtualBox allows `192.168.56.0/21` by default on Linux
and macOS. Leave capacity for the host and reset completed lab clusters.
The playbook requires at least 16 GiB assigned RAM and four CPUs; the larger
default leaves headroom for Rancher and a running lab. Concurrent labs share CPU,
memory and the VM kernel. This is a learning environment, not an HA deployment.

## Install on the laptop that will run the labs

Use the existing Bash, Vagrant, VirtualBox and Ansible controller prerequisites
in [the README](../README.md#one-vm-independent-labs). This checkout's local test
suite does not start or provision a VM.

```bash
vagrant validate
./lab.sh provision
./lab.sh platform
```

The first run downloads RKE2, its system images, Rancher and the lab images.
Downloads require working internet access and registry DNS. The installer checks
SHA-256 digests for the RKE2 archive, Helm archive and Rancher chart. It enables
`rke2-server`, waits for the API and node, installs the TLS secrets and Rancher,
checks DNS from a management Pod, and verifies HTTPS `/ping` with the private CA.
Only then does it write the new provisioning-complete marker.

Rancher uses a locally generated CA and a certificate for its configured DNS name.
This follows Rancher's `ingress.tls.source=secret` installation, so cert-manager
is not needed. The CA, key and initial password persist across provisioning runs.
No credentials are committed or printed by Ansible. Rerunning provision reconciles
Rancher at its pinned version and renews a leaf certificate with less than 30 days
remaining. It does not rotate the CA or change the user's Rancher login password.

## Open Rancher

1. Add `192.168.56.10 rancher.chaos.test` to the **laptop's** hosts file, using the
   values from `config/platform.yml` if changed. Provisioning configures the VM's
   hosts file and RKE2 CoreDNS; it does not edit the laptop.
2. Export the public lab CA from the VM:

   ```bash
   vagrant ssh chaos -c 'cat /home/vagrant/rancher/ca.crt' > rancher-lab-ca.crt
   ```

   Import that certificate into the browser or OS trusted roots. The private CA
   key stays under `/etc/chaos-platform/tls/` inside the VM. Do not bypass TLS checks.
3. Run `./lab.sh ssh`, then read `cat ~/rancher/bootstrap-password` privately.
   Open `https://rancher.chaos.test`, sign in as `admin`, set your own password,
   and confirm the displayed Rancher URL. The bootstrap password is for initial
   setup; after changing it, use your new password.

The local RKE2 cluster appears in Rancher as `local`. The disposable kind lab
clusters are **not automatically imported** into Rancher. This change installs
the management platform; the existing Kubernetes exercises still run on kind.
Automatically importing fault-injection clusters would add agents and admission
components to the controlled experiments and change what they measure.

## Run and reset labs

```bash
./lab.sh 03 setup
./lab.sh ssh
# Inside the VM:
rke2-kubectl get nodes               # permanent management cluster
source ~/labs/lab03/env.sh
k get nodes                         # disposable lab03 cluster
# Back on the laptop:
./lab.sh 03 reset
./lab.sh platform
```

RKE2's bundled kubectl is used by the management wrapper. Lab setup may replace
the shared `kubectl` with the version matching kind without changing management's
client. Neither installer merges into `~/.kube/config`. Lab reset removes only
the selected lab's kind cluster, files and declared resources. It never invokes
`rke2-uninstall.sh`, removes management storage, or deletes Rancher.

`./lab.sh stop` halts the entire VM, including management. `./lab.sh start` resumes
it; systemd starts RKE2 again. Run `./lab.sh platform` to verify recovery. That
command checks service health, API and node readiness, Rancher rollout, TLS, and the user's
management kubeconfig without changing cluster resources.

## Existing VMs and upgrades

Save old lab results and remove old fixtures with their matching checkout before
changing lab numbering. For an existing VM, apply the new resources and private
network with `vagrant reload chaos --no-provision`, then run `./lab.sh provision`.
No VM is destroyed automatically. An unmanaged existing RKE2 installation is
rejected rather than adopted. A managed platform IP or hostname cannot be silently
changed after installation; use a fresh VM or plan a migration.

Provisioning also rejects an installed RKE2 version different from the pin. This
is intentional: Kubernetes upgrades require backups and supported version steps.
Follow the upstream upgrade procedure, update the pin and both architecture
checksums together, then rerun provisioning. Do not downgrade RKE2. Back up the
RKE2 server token together with etcd snapshots, Rancher data and the private CA
before deleting a VM or changing versions. Snapshots within the same VM are not
protection against losing its disk.

## Verification and troubleshooting

Run `bash scripts/validate.sh` for the offline checks. They include all 27 labs,
54 cards, lifecycle routing, Ansible syntax, file installation, reset isolation,
certificate reuse/renewal, private-key modes, target guards and actual Ansible
template rendering. The real pinned Rancher chart can also be rendered locally
with Helm; this checks chart compatibility without claiming a successful deployment.

On the target laptop, acceptance requires successful provisioning, opening the
Rancher UI, a second provisioning run that preserves the CA and bootstrap file,
one container lab and one Kubernetes lab, reset followed by `./lab.sh platform`,
and a stop/start cycle. Live VM acceptance has not been run on this development
machine. No Linux service or Kubernetes cluster is started by the offline tests.

Inside the VM, inspect a failed installation with:

```bash
sudo systemctl status rke2-server
sudo journalctl -u rke2-server -n 100 --no-pager
rke2-kubectl get pods -A
rke2-kubectl -n cattle-system describe deployment rancher
rke2-kubectl -n cattle-system logs deployment/rancher --tail=100
```

A failed Helm installation uses `--atomic` to roll back. Fix DNS, available
resources, image downloads or certificate errors and rerun provision. Do not
remove `/var/lib/rancher/rke2` as a troubleshooting shortcut. If the CA is incomplete
or near expiry, the certificate helper fails explicitly instead of replacing the
trust root; restore its matching certificate/key backup or plan a CA rotation.

## Upstream references

- [Rancher 2.15.1 support matrix](https://www.suse.com/suse-rancher/support-matrix/all-supported-versions/rancher-v2-15-1/): RKE2 1.34 through 1.36 are supported management platforms.
- [RKE2 installation methods](https://docs.rke2.io/install/methods): tarball layout and systemd service installation.
- [RKE2 server configuration](https://docs.rke2.io/reference/server_config): networking, ingress, encryption and snapshots.
- [RKE2 networking services](https://docs.rke2.io/networking/networking_services): Traefik and CoreDNS HelmChartConfig settings.
- [Rancher installation](https://ranchermanager.docs.rancher.com/getting-started/installation-and-upgrade/install-upgrade-on-a-kubernetes-cluster/): private-CA certificates, Helm and initial login.
