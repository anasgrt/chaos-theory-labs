#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

restore_quorum() {
start_etcd lab14-control-plane2
start_etcd lab14-control-plane3
healthy=0
for i in $(seq 1 18); do
  if ec lab14-control-plane endpoint health --cluster; then healthy=1; break; fi
  sleep 5
done
test "$healthy" -eq 1 || echo 'STOP: use fallback; do not claim quorum recovery.'
echo "healthy=$healthy"
}

read_persisted_state() {
observed=0
for i in $(seq 1 18); do
  if h get configmap quorum-probe -o jsonpath='{.data.state}{" resourceVersion="}{.metadata.resourceVersion}{"\n"}' &&
     h get deployment quorum-web -o custom-columns=DESIRED:.spec.replicas,READY:.status.readyReplicas; then
    observed=1; break
  fi
  sleep 5
done
test "$observed" -eq 1 || echo 'STOP: retain the unknown result; do not overwrite it before readback works.'
ec lab14-control-plane endpoint status --cluster -w table
echo "observed=$observed"
}
