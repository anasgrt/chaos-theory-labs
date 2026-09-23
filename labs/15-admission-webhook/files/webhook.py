"""A validating admission webhook: Pods in scoped namespaces must carry an owner label."""
import json
import os
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REQUIRED = os.environ.get('REQUIRED_LABEL', 'owner')


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        self.reply(b'ok\n')  # the kubelet readiness probe uses this path

    def do_POST(self):
        review = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
        request = review.get('request') or {}
        metadata = (request.get('object') or {}).get('metadata') or {}
        allowed = REQUIRED in (metadata.get('labels') or {})
        print(f'review uid={request.get("uid")} namespace={request.get("namespace")} '
              f'pod={metadata.get("generateName") or metadata.get("name")} allowed={allowed}', flush=True)
        response = {
            'apiVersion': 'admission.k8s.io/v1',
            'kind': 'AdmissionReview',
            'response': {'uid': request.get('uid'), 'allowed': allowed},
        }
        if not allowed:
            response['response']['status'] = {
                'code': 403,
                'message': f'ce-lab15 policy: every Pod must carry the {REQUIRED} label',
            }
        self.reply(json.dumps(response).encode(), 'application/json')

    def reply(self, body, content_type='text/plain'):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('/tls/tls.crt', '/tls/tls.key')
server = ThreadingHTTPServer(('0.0.0.0', 8443), Handler)
server.socket = context.wrap_socket(server.socket, server_side=True)
print(f'admission webhook listening on 8443 required_label={REQUIRED}', flush=True)
server.serve_forever()
