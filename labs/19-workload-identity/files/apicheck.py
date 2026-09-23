"""Ask the Kubernetes API what this Pod's ServiceAccount may actually read."""
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

ROOT = '/var/run/secrets/kubernetes.io/serviceaccount'
API = f"https://{os.environ.get('KUBERNETES_SERVICE_HOST', 'kubernetes.default.svc')}:" \
      f"{os.environ.get('KUBERNETES_SERVICE_PORT', '443')}"


def read(name):
    try:
        return open(f'{ROOT}/{name}').read().strip()
    except OSError:
        return None


def claims(token):
    """Decode the token payload for its subject and expiry. This does not verify it."""
    payload = token.split('.')[1]
    payload += '=' * (-len(payload) % 4)
    body = json.loads(base64.urlsafe_b64decode(payload))
    return body.get('sub', '?'), body.get('exp', '?')


def request(path, token, context):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    try:
        with urllib.request.urlopen(urllib.request.Request(API + path, headers=headers),
                                    timeout=10, context=context) as response:
            items = json.loads(response.read()).get('items', [])
            return f'{response.status} items={len(items)}'
    except urllib.error.HTTPError as error:
        return f'{error.code} {json.loads(error.read()).get("message", "")[:150]}'
    except OSError as error:
        return f'transport error: {error}'


token = read('token')
namespace = read('namespace') or os.environ.get('POD_NAMESPACE', 'default')
authority = f'{ROOT}/ca.crt' if read('ca.crt') else None
context = ssl.create_default_context(cafile=authority) if authority else ssl._create_unverified_context()

if token:
    subject, expiry = claims(token)
    print(f'token=mounted subject={subject} expires_at={expiry}')
else:
    print('token=absent subject=none expires_at=none')
print(f'namespace={namespace} api={API} ca={"mounted" if authority else "absent"}')
for path in (f'/api/v1/namespaces/{namespace}/pods', '/api/v1/namespaces/kube-system/pods'):
    print(f'GET {path} -> {request(path, token, context)}')
