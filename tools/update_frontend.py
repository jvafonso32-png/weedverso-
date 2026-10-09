"""Update only the three UI files; keep the active host, backend and data intact."""
import argparse
import json
import shlex
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ('index.html', 'assets/touch-ui.css', 'assets/touch-ui.js')
INSTALLER = r'''
import json, os, shutil, sys, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1]).resolve()
archive = Path(sys.argv[2])
allowed = {'index.html', 'assets/touch-ui.css', 'assets/touch-ui.js'}
if not (root / 'index.html').is_file():
    raise SystemExit('Active index.html not found; no files changed')
with zipfile.ZipFile(archive) as bundle:
    if set(bundle.namelist()) != allowed:
        raise SystemExit('Unexpected files in UI package; no files changed')
    payload = {name: bundle.read(name) for name in allowed}
    if b'assets/touch-ui.js?v=1' not in payload['index.html']:
        raise SystemExit('UI package validation failed; no files changed')
for name in allowed:
    if not (root / name).resolve().is_relative_to(root):
        raise SystemExit('UI path leaves the active app directory; no files changed')

# Backups live outside the directory served by the app.
stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
backup_root = root.parent / 'ui-backups'
backup_root.mkdir(mode=0o700, exist_ok=True)
backup = backup_root / stamp
backup.mkdir(mode=0o700)
for name in allowed:
    source = root / name
    if source.is_file():
        target = backup / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
state = root / 'data' / 'shared_state.json'
if state.is_file():
    shutil.copy2(state, backup / 'shared_state.json')
    (backup / 'shared_state.json').chmod(0o600)

original = (root / 'index.html').stat()
installed = []
try:
    # Assets first; the running HTML is replaced atomically as the final step.
    for name in ('assets/touch-ui.css', 'assets/touch-ui.js', 'index.html'):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix='.weedverso-ui-', dir=target.parent)
        try:
            with os.fdopen(descriptor, 'wb') as file:
                file.write(payload[name])
            os.chmod(temporary, 0o644)
            os.chown(temporary, original.st_uid, original.st_gid)
            os.replace(temporary, target)
            installed.append(name)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
except Exception:
    for name in reversed(installed):
        prior = backup / name
        target = root / name
        if prior.is_file():
            shutil.copy2(prior, target)
        else:
            target.unlink(missing_ok=True)
    raise
print(json.dumps({'updated': list(installed), 'backup': str(backup), 'dataBackupMade': state.is_file(), 'restartRequired': False}))
'''


def run(command):
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Remote operation failed')
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host')
    parser.add_argument('--key', type=Path)
    parser.add_argument('--user', default='ec2-user')
    parser.add_argument('--app-dir', help='Omit to discover it from the active weedverso service')
    parser.add_argument('--package-only', type=Path, help='Create the UI-only zip without contacting the server')
    args = parser.parse_args()
    if not args.package_only and (not args.host or not args.key):
        parser.error('--host and --key are required for a remote update')
    for value in (args.host, args.user):
        if value is None:
            continue
        if not value or any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_' for char in value):
            parser.error('Host/user contains unsupported characters')
    with tempfile.TemporaryDirectory(prefix='weedverso-ui-') as temporary:
        directory = Path(temporary)
        package = directory / 'weedverso-interface.zip'
        with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as bundle:
            for relative in FILES:
                bundle.write(ROOT / 'app' / relative, relative)
        if args.package_only:
            args.package_only.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(package, args.package_only)
            print(json.dumps({'package': str(args.package_only.resolve()), 'files': list(FILES), 'includesFinancialData': False}))
            return
        if not args.key.is_file():
            parser.error('SSH key file not found')
        remote = f'{args.user}@{args.host}'
        options = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10', '-i', str(args.key)]
        ssh = ['ssh', *options, remote]
        app_dir = args.app_dir or run([*ssh, 'systemctl show weedverso --property=WorkingDirectory --value'])
        if not app_dir.startswith('/') or app_dir == '/':
            raise RuntimeError('Could not identify the active application directory; nothing uploaded')
        remote_temp = run([*ssh, 'mktemp -d /tmp/weedverso-ui.XXXXXX'])
        if not remote_temp.startswith('/tmp/weedverso-ui.') or any(c.isspace() for c in remote_temp):
            raise RuntimeError('Unexpected temporary directory')
        installer = directory / 'install_ui.py'
        installer.write_text(INSTALLER, encoding='utf-8')
        run(['scp', *options, str(package), str(installer), f'{remote}:{remote_temp}/'])
        command = ' '.join(shlex.quote(arg) for arg in ['sudo', '-n', 'python3', remote_temp+'/install_ui.py', app_dir, remote_temp+'/weedverso-interface.zip'])
        print(run([*ssh, command]))


if __name__ == '__main__':
    main()
