"""Prepare two valid encryption configurations and matching static Pod manifests."""
import base64
from copy import deepcopy
import json
import os
from pathlib import Path


def prepare(workspace):
    original = json.loads((workspace / 'apiserver-observed.json').read_text())
    spec = original['spec']
    containers = spec['containers']
    if len(containers) != 1 or containers[0]['name'] != 'kube-apiserver':
        raise ValueError('Expected exactly one kube-apiserver container')
    if any(arg.startswith('--encryption-provider-config') for arg in containers[0]['command']):
        raise ValueError('Baseline already configures encryption; refusing to overwrite it')
    for name in ('key1', 'key2'):
        configuration = {
            'apiVersion': 'apiserver.config.k8s.io/v1', 'kind': 'EncryptionConfiguration',
            'resources': [{'resources': ['secrets'], 'providers': [
                {'aescbc': {'keys': [{'name': f'lab-{name}', 'secret': base64.b64encode(os.urandom(32)).decode()}]}},
                {'identity': {}}]}]}
        manifest = {'apiVersion': 'v1', 'kind': 'Pod',
                    'metadata': {'name': 'kube-apiserver', 'namespace': 'kube-system',
                                 'annotations': {'chaos-labs/provider': name}},
                    'spec': deepcopy(spec)}
        container = manifest['spec']['containers'][0]
        container['command'].append(f'--encryption-provider-config=/etc/kubernetes/ce-lab36/provider-{name}.json')
        container['volumeMounts'].append({'name': 'ce-lab36-encryption', 'mountPath': '/etc/kubernetes/ce-lab36', 'readOnly': True})
        manifest['spec']['volumes'].append({'name': 'ce-lab36-encryption', 'hostPath': {'path': '/etc/kubernetes/ce-lab36', 'type': 'Directory'}})
        for filename, value in ((f'provider-{name}.json', configuration), (f'apiserver-{name}.json', manifest)):
            path = workspace / filename
            path.write_text(json.dumps(value, indent=2) + '\n')
            path.chmod(0o600)


if __name__ == '__main__':
    prepare(Path.home() / 'labs/lab36')
