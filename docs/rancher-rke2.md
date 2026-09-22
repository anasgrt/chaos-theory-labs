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
# macOS: configure browser access in an interactive Terminal
./lab.sh browser-setup
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
is not needed. The CA and key persist across provisioning runs. Rerunning provision
reconciles Rancher at its pinned version and renews a leaf certificate with less
than 30 days remaining; it does not rotate the CA.

Every successful provision sets the local `admin` password to `SuperAdmin@123`
(the `rancher_admin_password` value in `config/platform.yml`) and prints the URL,
username and password for copying into the UI. This deliberately overwrites any
password set through the UI and exposes the lab credential in provisioning logs.
Use this behavior only for this local teaching environment.

The chart receives the same initial bootstrap password, but that alone does not
change an existing account. After Rancher is ready, Ansible identifies the default
admin and submits a `PasswordChangeRequest` through the management Kubernetes API.
It then verifies a real HTTPS login and revokes the short-lived verification token.
A failed reset or login fails provisioning before the login summary is printed.
`./lab.sh platform` and `./lab.sh browser-setup` do not reset or print the password.
For compatibility, `~/rancher/bootstrap-password` contains the configured password
and is refreshed on each provision, with mode `0600`.

## Open Rancher

On **macOS**, run this once after provisioning, from an interactive Mac Terminal:

```bash
./lab.sh browser-setup
```

The command verifies the VM identity and platform health, exports only the public
CA, and reads the IP/hostname from `config/platform.yml` through Ansible. It
verifies HTTPS from the laptop before changing its settings. It then updates the
configured hostname in `/etc/hosts`, preserving other aliases and comments and
saving a backup under `/etc/hosts.chaos-backup.*` when a change is needed. Finally,
it trusts the lab CA for SSL in the system keychain and runs `./lab.sh platform`.
Approve administrator authentication when prompted; do not run the entire command
with `sudo`. Python 3 is required on the laptop; no extra Python packages are used
by this helper.

These settings survive Mac and VM restarts. Repeated runs do not duplicate the
hostname entry or reinstall an already trusted CA. Rerun after recreating the VM
with a new CA, or after removing the laptop configuration. Normal provisioning
preserves the CA, including when renewing its server certificate. The helper does
not remove old trusted CAs or hostnames belonging to other configurations.

`browser-setup` currently supports macOS. Linux users should follow the manual
steps below. Provisioning and `platform` never silently change laptop trust.

### Manual setup and diagnosis

The VM health check cannot prove browser access. Its `curl --resolve` supplies
an address directly, bypassing DNS, and `--cacert` supplies the VM's private CA.
Your laptop needs both hostname resolution and certificate trust independently.
`DNS_PROBE_FINISHED_NXDOMAIN` means the browser cannot resolve the hostname; it
has not reached Rancher or checked its certificate yet.

Run these commands **on the laptop**, from the repository root. These examples
use the defaults; substitute the values from `config/platform.yml` if changed.

1. Add the hostname to the laptop's `/etc/hosts`. On macOS:

   ```bash
   # If this hostname already exists, correct that entry instead of adding another.
   sudo sh -c 'printf "\n192.168.56.10 rancher.chaos.test\n" >> /etc/hosts'
   sudo dscacheutil -flushcache
   sudo killall -HUP mDNSResponder
   dscacheutil -q host -a name rancher.chaos.test
   ```

   The last command should report `192.168.56.10`. Linux also uses `/etc/hosts`;
   check it with `getent hosts rancher.chaos.test`. Provisioning edits only the
   VM's hosts file and RKE2 CoreDNS. Those changes do not configure laptop DNS.

2. Export the public CA and trust it. `./lab.sh platform` also exports this file
   before checking laptop access:

   ```bash
   vagrant ssh chaos -c 'cat /home/vagrant/rancher/ca.crt' > rancher-lab-ca.crt
   # macOS: trust this lab CA for SSL in the system keychain.
   sudo security add-trusted-cert -d -r trustRoot -p ssl \
     -k /Library/Keychains/System.keychain "$PWD/rancher-lab-ca.crt"
   ```

   On Linux, import the certificate into the OS/browser trusted roots using
   your distribution/browser's certificate manager. Only the public certificate
   is exported; the CA private key stays inside the VM. Do not bypass TLS checks.
   A curl build using a separate CA bundle needs that bundle configured too.

3. Verify access from the laptop and open the explicit HTTPS URL:

   ```bash
   ./lab.sh platform
   curl --noproxy '*' --fail https://rancher.chaos.test/ping
   ```

   Expect `pong`. Open `https://rancher.chaos.test`. If Chrome retains the previous
   DNS/certificate error, fully quit and reopen it after completing steps 1–2.
   Browser-specific proxy settings and certificate stores still need a browser check.

4. Sign in as `admin` with `SuperAdmin@123`, or copy the credentials printed at
   the end of provisioning if you changed `rancher_admin_password`. A UI password
   change lasts only until the next provision, which restores the configured value.

The local RKE2 cluster appears in Rancher as `local`. Each Kubernetes lab's kind
cluster is registered beside it under its own name during `./lab.sh NN setup`, and
removed again during `./lab.sh NN reset`. The labs still run entirely on kind; only
the view is shared. See [Lab clusters in Rancher](#lab-clusters-in-rancher).

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

## Lab clusters in Rancher

`./lab.sh NN setup` registers that lab's kind cluster with Rancher after creating
it, so `lab03` appears under Cluster Management next to `local` and its Pods,
nodes and events are visible in the UI. `./lab.sh NN reset` removes the cluster
from Rancher first, while its agent can still be reached, and only then deletes
the kind cluster. Setting the same lab up twice reuses its existing record rather
than adding a second entry.

Registration is done through Rancher's API as `admin`, using the password in
[config/platform.yml](../config/platform.yml) and the private CA for verification.
A `provisioning.cattle.io` cluster applied with kubectl instead is stamped with the
creator `system:admin`, which is not a Rancher user, and its registration token is
then never issued. Provisioning publishes Rancher's `server-url` setting for the
same reason: while it is empty, Rancher issues registration tokens with no manifest
URL and no downstream cluster can register at all.

Lab Pods reach `rancher.chaos.test` through the VM's own resolver, which
provisioning already points at the VM hosts file, so no cluster DNS changes are
made inside kind. The lab cluster pulls `rancher/rancher-agent` from the registry
when it registers, which adds a few minutes to the first Kubernetes setup after a
new cluster is created. The image is not preloaded: copying 1.5 GiB into all four
kind nodes is slower than one pull and exceeds the image loader's per-image
timeout. Registration therefore needs working registry access, like lab setup.

`./lab.sh reset-all` removes every installed lab in one run, each with its own
Rancher entry, and asks for confirmation first.

Reset is the recovery path and is never blocked by the platform. If Rancher is
stopped, broken or not yet provisioned, reset still deletes the lab and reports the
cluster entry to remove by hand under Cluster Management.

Registration puts Rancher's agent inside the cluster under test. That is extra
moving parts in a controlled experiment: it reschedules during a node failure,
adds a Pod to evict during a drain, and appears in any cluster-wide inventory.
Labs whose measurements are cluster-wide, such as 06, 09, 13 and 17, are the ones
most affected. Set `rancher_import_labs: false` in
[config/platform.yml](../config/platform.yml) to run every lab on a plain kind
cluster; existing lab clusters are then left alone until their next reset.

RKE2's bundled kubectl is used by the management wrapper. Lab setup may replace
the shared `kubectl` with the version matching kind without changing management's
client. Neither installer merges into `~/.kube/config`. Lab reset removes only
the selected lab's kind cluster, its own Rancher cluster entry, files and declared
resources. It never invokes `rke2-uninstall.sh`, removes management storage,
deletes Rancher, or touches the `local` cluster.

`./lab.sh stop` halts the entire VM, including management. `./lab.sh start` resumes
it; systemd starts RKE2 again. Run `./lab.sh platform` to verify recovery. That
command checks service health, API and node readiness, Rancher rollout, TLS, and
the user's management kubeconfig. It then exports the public CA and checks laptop
DNS, HTTPS without a DNS override, and default curl certificate trust. A failure
identifies the layer and points to the setup steps above. It does not change
cluster resources, the laptop hosts file, or trusted roots.

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
certificate reuse/renewal, private-key modes, target guards, cluster registration
and removal against a stub Rancher API, and actual Ansible template rendering. The real pinned Rancher chart can also be rendered locally
with Helm; this checks chart compatibility without claiming a successful deployment.

On the target laptop, acceptance requires successful provisioning, opening the
Rancher UI, a second provisioning run that preserves the CA and restores the configured admin password,
one container lab and one Kubernetes lab, that Kubernetes lab appearing in Rancher
as an active cluster and disappearing again after its reset, reset followed by
`./lab.sh platform`, and a stop/start cycle. Live VM acceptance has not been run on this development
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

Password reconciliation uses the [Rancher user/password API](https://ranchermanager.docs.rancher.com/api/workflows/users).
