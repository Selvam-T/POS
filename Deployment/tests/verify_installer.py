"""Explicit integration check: install/reinstall/uninstall only in a disposable workspace.

This is not run by unittest discovery. It compiles a test copy with no elevation,
system shortcuts, application launch, or uninstall registry entry. Data-copy and
data-preservation rules are taken directly from the real installer template.
"""

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import uuid


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_installer as installer


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(iscc=None):
    compiler = installer.find_compiler(iscc)
    stage, version, name = installer.prepare_inputs()
    if not stage.resolve().is_relative_to((installer.PRODUCTION / 'build').resolve()):
        raise ValueError('Integration tests must stay inside Production/build')
    template = installer.INSTALLER_SCRIPT.read_text(encoding='utf-8')
    # Change installation scope and omit desktop integration in the disposable copy.
    # File, directory, and version rules remain identical to the production script.
    lines = []
    section = ''
    for line in template.splitlines():
        if line.startswith('['):
            section = line
        if section in ('[Icons]', '[Run]', '[Tasks]'):
            continue
        if line.startswith('AppId='):
            line = 'AppId={{' + str(uuid.uuid4()).upper() + '}'
        if line == 'PrivilegesRequired=admin':
            line = 'PrivilegesRequired=lowest\nCreateUninstallRegKey=no'
        lines.append(line)
    script = stage / 'SelvamPOS-test.iss'
    script.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    output = stage / 'test-output'
    installer.compile_installer(compiler, script, stage, name, output)
    setup = output / f'SelvamPOS-Setup-{version}.exe'
    client = stage / 'test-client'
    env = os.environ.copy()
    (stage / 'temp').mkdir()
    env['TEMP'] = str(stage / 'temp')
    env['TMP'] = env['TEMP']
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0

    def run(executable, *args):
        subprocess.run([str(executable), '/VERYSILENT', '/SUPPRESSMSGBOXES',
                        '/NORESTART', '/SP-', *args], cwd=stage, env=env,
                       startupinfo=startup, timeout=120, check=True)

    run(setup, f'/DIR={client}', f'/LOG={stage / "fresh-install.log"}')
    for folder in ('db', 'runtime_data/json', 'runtime_data/ads', 'live_logs', 'backups'):
        assert (client / folder).is_dir(), folder
    assert (client / 'USERGUIDE.md').is_file()
    assert list((client / 'runtime_data').rglob('.gitkeep')) == []
    with closing(sqlite3.connect(client / 'db' / name)) as database:
        assert database.execute('PRAGMA quick_check').fetchone() == ('ok',)
    for source in (stage / 'seed' / 'runtime_data').rglob('*'):
        if source.is_file():
            assert digest(client / 'runtime_data' / source.relative_to(stage / 'seed' / 'runtime_data')) == digest(source)

    # Modify both installed seed content and newly created business data.
    database_path = client / 'db' / name
    with closing(sqlite3.connect(database_path)) as database:
        database.execute('CREATE TABLE _installer_preservation_test (value TEXT)')
        database.execute("INSERT INTO _installer_preservation_test VALUES ('client data')")
        database.commit()
    preserved = [database_path]
    for relative, content in (
        ('runtime_data/json/greeting.json', b'{"client": "custom greeting"}'),
        ('runtime_data/json/client-only.json', b'{"preserve": true}'),
        ('live_logs/error.log', b'client runtime log\n'),
        ('backups/client-backup.db', b'client backup content'),
    ):
        path = client / relative
        path.write_bytes(content)
        preserved.append(path)
    seed_ads = sorted((client / 'runtime_data' / 'ads').glob('*'))
    ad = next((path for path in seed_ads if path.is_file()), client / 'runtime_data' / 'ads' / 'client-ad.png')
    ad.write_bytes(b'client-custom-ad')
    preserved.append(ad)
    expected = {path: digest(path) for path in preserved}
    # Reinstall must restore application files while leaving all client data intact.
    (client / 'app' / 'SelvamPOS.exe').write_bytes(b'old application placeholder')
    run(setup, f'/DIR={client}', f'/LOG={stage / "reinstall.log"}')
    for path, fingerprint in expected.items():
        assert digest(path) == fingerprint, f'Reinstall changed {path}'
    for source in (stage / 'app').rglob('*'):
        if source.is_file():
            assert digest(client / 'app' / source.relative_to(stage / 'app')) == digest(source)

    run(client / 'app' / 'unins000.exe', f'/LOG={stage / "uninstall.log"}')
    # The uninstaller may complete its work in a temporary child process.
    for _ in range(100):
        if not (client / 'app' / 'SelvamPOS.exe').exists():
            break
        time.sleep(0.1)
    assert not (client / 'app' / 'SelvamPOS.exe').exists()
    assert not (client / 'USERGUIDE.md').exists()
    for path, fingerprint in expected.items():
        assert digest(path) == fingerprint, f'Uninstall changed {path}'
    for folder in ('db', 'runtime_data/json', 'runtime_data/ads', 'live_logs', 'backups'):
        assert (client / folder).is_dir(), folder
    report = {
        'result': 'PASS', 'version': version, 'workspace': str(stage),
        'checks': ['fresh install and seed data', 'application replacement on reinstall',
                   'existing database, JSON, ads, logs and backups preserved on reinstall',
                   'application removal with client data preserved on uninstall'],
    }
    (stage / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iscc', type=Path)
    args = parser.parse_args()
    verify(args.iscc)
