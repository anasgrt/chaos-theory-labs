# Review — Labs 30–32 (Secrets, network segmentation, authorization)

These three labs extend the security set against the
[OWASP Kubernetes Top 10 (2025)](https://kubernetes-top10.owasp.org/): K03
Secrets management failures, K05 missing network segmentation controls, and the
authorization half of K02. Each claim below was measured on a four-node kind
cluster built from `ansible/files/kubernetes/kind.yaml` running Kubernetes
v1.37.0, on 2026-09-21.

## Coverage against the existing labs

| Lab | Risk covered | Not already covered by |
| --- | --- | --- |
| 30 | K03 — where a Secret's value rests, and who can read it | 29 reads a ServiceAccount token; nothing read the stored object |
| 31 | K05 — what a NetworkPolicy stops and what it does not | 20 and 24 break naming and routing; nothing restricted traffic |
| 32 | K02 — grants that reach further than they name | 29 shows a grant taking effect; nothing performed an escalation |

## Lab 30 — measured

| Observation | Result |
| --- | --- |
| `.data.password` | `bGFiMzAtb3JpZ2luYWw=`, decoding to `lab30-original` |
| `kubectl describe` | `password: 14 bytes`, no value |
| `--encryption-provider-config` in the API server manifest | 0 matches, so the identity provider is in use |
| Stored object in etcd | 618 bytes; printable runs end `password`, `lab30-original`, `Opaque` |
| Environment consumer | `env_var` and `proc_1_environ` both hold the value; no mounted file |
| File consumer | tmpfs file, mode 644, target `..2026_09_21_09_39_38.1752655298/password`; no environment variable |
| `can-i get secrets` for the file consumer's account | `no`, exit 1, while the mounted file still holds the value |
| Rotation | mounted file changed after **82 s**; the environment variable still read `lab30-original` in the same running container |

The rotation delay is the kubelet's sync period and is reported by the step
itself, so a learner records the number they observe rather than this one.

## Lab 31 — measured

`kindest/kindnetd:v20260820-69b56db7` runs a policy controller, so this cluster
enforces NetworkPolicy. That was checked before the lab was written: an
accepted policy object is not evidence of enforcement.

| Policy in place | Labelled client | Unlabelled client | DNS from the labelled client |
| --- | --- | --- | --- |
| None | `ok status=200` in 10 ms | `ok status=200` in 11 ms | resolved in 3 ms |
| Default deny ingress | timed out at 5012 ms | timed out at 5026 ms | — |
| Allow `role: allowed` | `ok status=200` in 14 ms | timed out at 5011 ms | — |
| Default deny egress | request by IP timed out at 5015 ms | resolved in 3 ms (not selected) | failed `gaierror` after 20 024 ms |
| Egress to `kube-dns` allowed | request timed out at 5017 ms | — | resolved in 3 ms |
| Policies removed | `ok status=200` in 10 ms | `ok status=200` in 10 ms | resolved in 2 ms |

Two card claims were corrected after the first run: the step that denies egress
now contrasts DNS from the client the policy does not select, and the theory no
longer describes the restored lookup as a "fast failure" — in this fixture the
Service exists, so resolution succeeds in milliseconds while the connection
still times out.

## Lab 32 — measured

| Step | Result |
| --- | --- |
| `can-i create pods` / `can-i get secrets` for `builder` | `yes` / `no` (exit 1) |
| Probe in the builder's own Pod | `secrets -> 403 ... cannot list resource "secrets"` |
| Builder creates a Pod with `serviceAccountName: secret-reader` | accepted, exit 0 |
| Probe inside that Pod | `subject=system:serviceaccount:ce-lab32:secret-reader`, `secrets -> 200 items=1 names=app-credentials` |
| `role-writer` creates a Role within its rights | created |
| The same account adds `get secrets` | `Forbidden ... attempting to grant RBAC permissions not currently held: {APIGroups:[""], Resources:["secrets"], Verbs:["get"]}` |
| `can-i create pods/exec` | `yes` |
| `can-i create pods --subresource=exec` | `no` |
| `SubjectAccessReview` with `subresource: exec` | `false` |
| `kubectl exec` as the builder | `cannot create resource "pods/exec"` |

The four authorization answers are the point of the last step: the convenient
slashed form is the one that disagrees with the operation.

## Not validated here

The Vagrant VM path, AMD64 hosts and `kind load` image preloading were not
exercised; these labs pull `python:3.12-slim` from the registry like the rest of
the Kubernetes set. `docs/chaos-labs.pdf` still covers Labs 00–21 and needs
regenerating to include Labs 22–32.
