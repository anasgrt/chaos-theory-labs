"""Ask the API, as this Pod, for the namespace's Secrets and report the answer."""
import base64
import json
import pathlib
import ssl
import sys
import urllib.error
import urllib.request

BASE = pathlib.Path('/var/run/secrets/kubernetes.io/serviceaccount')


def identity(token):
    payload = token.split('.')[1]
    payload += '=' * (-len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    return claims.get('sub', 'unknown')


def request(token, namespace, resource):
    url = f'https://kubernetes.default.svc/api/v1/namespaces/{namespace}/{resource}'
    context = ssl.create_default_context(cafile=str(BASE / 'ca.crt'))
    call = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    try:
        with urllib.request.urlopen(call, context=context, timeout=10) as response:
            body = json.load(response)
            names = [item['metadata']['name'] for item in body.get('items', [])]
            return f'{resource} -> {response.status} items={len(names)} names={",".join(sorted(names)) or "none"}'
    except urllib.error.HTTPError as error:
        message = json.loads(error.read() or b'{}').get('message', '')
        return f'{resource} -> {error.code} {message}'
    except Exception as error:
        return f'{resource} -> unreachable {type(error).__name__}'


def main():
    if not (BASE / 'token').exists():
        print('token=absent')
        return 1
    token = (BASE / 'token').read_text()
    namespace = (BASE / 'namespace').read_text().strip()
    print(f'subject={identity(token)}')
    print(f'namespace={namespace}')
    print(request(token, namespace, 'secrets'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
