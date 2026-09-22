#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

shutdown_settings() {
k get deployment drain-web -o json | jq '{replicas:.spec.replicas,grace:.spec.template.spec.terminationGracePeriodSeconds,lifecycle:.spec.template.spec.containers[0].lifecycle,shutdown:[.spec.template.spec.containers[0].env[]|select(.name=="SHUTDOWN").value]}'
}
