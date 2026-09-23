#!/usr/bin/env python3
"""Explicit macOS browser setup; never called by provisioning or lab actions."""
import base64
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HOSTS = Path('/etc/hosts')
SYSTEM_KEYCHAIN = '/Library/Keychains/System.keychain'


def validate(ip, hostname):
    if ipaddress.ip_address(ip).version != 4:
        raise ValueError('The platform address must be IPv4.')
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+', hostname):
        raise ValueError('Invalid Rancher hostname.')


def update_hosts(content, ip, hostname):
    """Replace only this hostname, keeping other aliases and comments intact."""
    validate(ip, hostname)
    result = []
    for line in content.splitlines(keepends=True):
        entry, marker, comment = line.partition('#')
        fields = entry.split()
        if len(fields) < 2 or hostname.lower() not in [value.lower() for value in fields[1:]]:
            result.append(line)
            continue
        aliases = [value for value in fields[1:] if value.lower() != hostname.lower()]
        if aliases:
            result.append(fields[0] + '\t' + ' '.join(aliases) + (' #' + comment.rstrip('\n') if marker else '') + '\n')
        elif marker:
            result.append('#' + comment.rstrip('\n') + '\n')
    text = ''.join(result)
    return text + ('' if not text or text.endswith('\n') else '\n') + f'{ip} {hostname}\n'


def install_hosts(ip, hostname):
    if os.geteuid() != 0:
        raise RuntimeError('Updating /etc/hosts requires sudo.')
    original = HOSTS.read_text()
    updated = update_hosts(original, ip, hostname)
    if original == updated:
        return
    # A unique backup for each actual change; preserve the original file's mode
    # and ownership by writing through it instead of replacing it with a temp file.
    with tempfile.NamedTemporaryFile(prefix='hosts.chaos-backup.', dir='/etc', mode='w', delete=False) as backup:
        backup.write(original)
        print(f'Hosts backup: {backup.name}', flush=True)
    HOSTS.write_text(updated)


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def pem_certificates(bundle):
    """Every certificate block in a PEM listing, in the order given."""
    return re.findall(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', bundle, re.S)


def certificate_digests(pem):
    """The SHA-1 and SHA-256 digests macOS identifies a certificate by."""
    body = ''.join(line for line in pem.splitlines() if 'CERTIFICATE' not in line)
    der = base64.b64decode(body)
    return hashlib.sha1(der).hexdigest().upper(), hashlib.sha256(der).hexdigest().upper()


def superseded_certificates(bundle, current_pem):
    """SHA-1 digests of same-named lab CAs that are not the current one.

    Recreating the VM mints a new CA under the same name. macOS only ever adds
    trust, so every rebuild leaves another trusted root behind, and a browser
    validating today's certificate against a dead root fails in a way that is
    hard to read. Identity is taken from the digest, never from the name.
    """
    current = certificate_digests(current_pem)[1]
    stale = []
    for block in pem_certificates(bundle):
        sha1, sha256 = certificate_digests(block)
        if sha256 != current and sha1 not in stale:
            stale.append(sha1)
    return stale


def common_name(pem_path):
    subject = run('/usr/bin/openssl', 'x509', '-in', str(pem_path), '-noout', '-subject',
                  '-nameopt', 'RFC2253', capture_output=True, text=True).stdout
    match = re.search(r'CN=([^,\n]+)', subject)
    if not match:
        raise RuntimeError('The exported lab CA has no common name.')
    return match.group(1).strip()


def prune_superseded_cas(ca_path, keychain=SYSTEM_KEYCHAIN):
    """Remove the lab CAs this one replaced, reporting each removal.

    Scope is deliberately narrow: only certificates sharing this CA's own
    common name, and only those whose digest differs from the CA now in use.
    A certificate with any other subject, and the current CA itself, are never
    touched. Removal is automatic because a stale same-named root left behind
    by a rebuilt VM breaks the browser in a way that is hard to read.
    """
    current_pem = Path(ca_path).read_text()
    name = common_name(ca_path)
    listing = subprocess.run(['/usr/bin/security', 'find-certificate', '-c', name, '-a', '-p', keychain],
                             capture_output=True, text=True)
    stale = superseded_certificates(listing.stdout, current_pem)
    if not stale:
        return []
    print(f'Removing {len(stale)} superseded "{name}" certificate(s) left by an earlier VM.', flush=True)
    for sha1 in stale:
        run('sudo', '/usr/bin/security', 'delete-certificate', '-Z', sha1, keychain)
        print(f'Removed superseded lab CA {sha1}', flush=True)
    return stale


def main():
    if sys.platform != 'darwin':
        raise RuntimeError('browser-setup currently supports macOS. See docs/rancher-rke2.md#open-rancher for Linux.')
    if len(sys.argv) == 4 and sys.argv[1] == '--hosts-only':
        install_hosts(sys.argv[2], sys.argv[3])
        return
    if len(sys.argv) != 1 or os.geteuid() == 0:
        raise RuntimeError('Run ./lab.sh browser-setup as your normal user; it requests sudo only where needed.')
    run(str(ROOT / 'scripts/run-ansible.sh'), 'platform', '--playbook', str(ROOT / 'ansible/browser-export.yml'))
    config = json.loads((ROOT / '.vagrant/browser-access.json').read_text())
    ip, hostname = config['ip'], config['hostname']
    validate(ip, hostname)
    ca = str(ROOT / 'rancher-lab-ca.crt')
    # Verify the host-to-VM path and certificate before installing trust.
    response = run('/usr/bin/curl', '--fail', '--silent', '--show-error', '--noproxy', '*',
                   '--connect-timeout', '5', '--max-time', '15', '--cacert', ca,
                   '--resolve', f'{hostname}:443:{ip}', f'https://{hostname}/ping',
                   capture_output=True, text=True)
    if response.stdout != 'pong':
        raise RuntimeError('Rancher did not return pong; laptop settings were not changed.')
    original = HOSTS.read_text()
    if update_hosts(original, ip, hostname) != original:
        print(f'Configuring laptop hosts: {ip} {hostname}. Enter your Mac password if prompted.', flush=True)
        run('sudo', sys.executable, str(Path(__file__).resolve()), '--hosts-only', ip, hostname)
        run('sudo', '/usr/bin/dscacheutil', '-flushcache')
        run('sudo', '/usr/bin/killall', '-HUP', 'mDNSResponder')
    trusted = subprocess.run(['/usr/bin/security', 'verify-cert', '-c', ca, '-p', 'ssl'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if trusted.returncode:
        print('Trusting the public lab CA for SSL. Approve macOS authentication if prompted.', flush=True)
        run('sudo', '/usr/bin/security', 'add-trusted-cert', '-d', '-r', 'trustRoot', '-p', 'ssl',
            '-k', SYSTEM_KEYCHAIN, ca)
    prune_superseded_cas(ca)
    run(str(ROOT / 'lab.sh'), 'platform')
    print(f'Browser setup complete. Open https://{hostname}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit(f'Browser setup failed: {error}\nRun ./lab.sh browser-setup in an interactive Mac Terminal. It is safe to retry.')
