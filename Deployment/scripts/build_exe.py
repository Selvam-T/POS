"""Validate inputs and build the Windows onedir application with PyInstaller."""

import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from generate_version_info import generate


DEPLOYMENT = Path(__file__).resolve().parents[1]
GENERATED = DEPLOYMENT / 'generated'
ROOT = DEPLOYMENT.parent
SOURCE = ROOT / 'Development' / 'src'
PRODUCTION = ROOT / 'Production'
APP = PRODUCTION / 'dist' / 'SelvamPOS'
DEPENDENCIES = ('PyInstaller', 'PyQt5', 'pynput', 'lxml', 'jsbeautifier',
                'escpos', 'openpyxl', 'xlwt', 'qrcode', 'PIL')


def production_mode(config):
    tree = ast.parse(config.read_text(encoding='utf-8-sig'))
    assignments = [node.value for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'PRODUCTION_MODE'
                           for t in node.targets)]
    if len(assignments) != 1:
        raise ValueError('config.py must assign PRODUCTION_MODE exactly once')
    value = ast.literal_eval(assignments[0])
    if type(value) is not bool:
        raise ValueError('PRODUCTION_MODE must be literal True or False')
    return value


def validate_mode(config, development):
    mode = production_mode(config)
    if not mode and not development:
        raise ValueError('Production build requires PRODUCTION_MODE = True. '
                         'For a packaging test only, use --development.')
    if mode and development:
        raise ValueError('--development requires PRODUCTION_MODE = False')
    return mode


def source_digest():
    """Fingerprint packaged inputs; installer can detect source/build mismatch."""
    digest = hashlib.sha256()
    paths = [p for p in SOURCE.rglob('*.py')
             if not {'tests', 'dev_tools', '__pycache__'}.intersection(p.relative_to(SOURCE).parts)]
    for folder in ('assets', 'ui'):
        paths.extend(p for p in (SOURCE / folder).rglob('*') if p.is_file())
    for path in sorted(set(paths)):
        digest.update(path.relative_to(SOURCE).as_posix().encode('utf-8') + b'\0')
        digest.update(path.read_bytes())
    return digest.hexdigest()


def package_digest(app):
    """Fingerprint all distributed files, excluding the manifest itself."""
    digest = hashlib.sha256()
    for path in sorted(app.rglob('*')):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f'Package must not contain linked paths: {path}')
        if not path.is_file() or path == app / 'build_metadata.json':
            continue
        digest.update(path.relative_to(app).as_posix().encode('utf-8') + b'\0')
        with path.open('rb') as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
    return digest.hexdigest()


def build(development=False):
    if sys.platform != 'win32':
        raise ValueError('Build the Windows executable on Windows')
    if sys.version_info[:3] != (3, 12, 10):
        raise ValueError('Use the verified Python 3.12.10 project environment')
    config = SOURCE / 'config.py'
    mode = validate_mode(config, development)
    for path in (SOURCE / 'main.py', SOURCE / 'assets' / 'ico' / 'selvampos.ico',
                 SOURCE / 'ui', SOURCE / 'assets'):
        if not path.exists():
            raise ValueError(f'Missing build input: {path}')
    missing = [name for name in DEPENDENCIES if importlib.util.find_spec(name) is None]
    if missing:
        raise ValueError('Missing dependencies: ' + ', '.join(missing) +
                         '. Install Development/requirements.txt and Deployment/requirements-build.txt.')

    # Generate before PyInstaller; exceptions prevent packaging stale metadata.
    version = generate(config, GENERATED)
    before = source_digest()
    work = PRODUCTION / 'build'
    for directory in (work, PRODUCTION / 'dist', PRODUCTION / 'release'):
        directory.mkdir(parents=True, exist_ok=True)
    # An unsuccessful rebuild must not retain a success marker from an older build.
    manifest = APP / 'build_metadata.json'
    manifest.unlink(missing_ok=True)
    env = os.environ.copy()
    env['PYINSTALLER_CONFIG_DIR'] = str(work / 'cache')
    command = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm', '--onedir', '--windowed', '--noupx',
        '--name', 'SelvamPOS', '--contents-directory', '_internal',
        '--workpath', str(work), '--distpath', str(PRODUCTION / 'dist'),
        '--specpath', str(work), '--paths', str(SOURCE),
        '--icon', str(SOURCE / 'assets' / 'ico' / 'selvampos.ico'),
        '--version-file', str(GENERATED / 'version_info.txt'),
        '--add-data', f'{SOURCE / "ui"}:ui',
        '--add-data', f'{SOURCE / "assets"}:assets',
        # Admin export imports are selected dynamically.
        '--hidden-import', 'xlwt', '--hidden-import', 'openpyxl',
        '--collect-data', 'escpos', '--copy-metadata', 'python-escpos',
        str(SOURCE / 'main.py'),
    ]
    print(f'Building SelvamPOS {version} ({"production" if mode else "DEVELOPMENT ONLY"})', flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    if not (APP / 'SelvamPOS.exe').is_file() or not (APP / '_internal').is_dir():
        raise ValueError('PyInstaller did not produce the expected executable layout')
    if before != source_digest():
        raise ValueError('Packaged inputs changed during the build; rebuild before distribution')
    metadata = {
        'app_version': version,
        'production_mode': mode,
        'source_sha256': before,
        'executable_sha256': hashlib.sha256((APP / 'SelvamPOS.exe').read_bytes()).hexdigest(),
        'package_sha256': package_digest(APP),
        'python_version': platform.python_version(),
    }
    manifest.write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(f'Build complete: {APP / "SelvamPOS.exe"}')
    if not mode:
        print('DEVELOPMENT ONLY: login bypass is embedded. Do not distribute to clients.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development', action='store_true',
                        help='Explicit packaging test with PRODUCTION_MODE=False; not for distribution')
    args = parser.parse_args(argv)
    try:
        build(args.development)
    except (OSError, ValueError, SyntaxError, subprocess.CalledProcessError) as exc:
        print(f'Executable build failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
