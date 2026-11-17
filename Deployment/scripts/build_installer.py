"""Validate the production package, snapshot starter data, and compile Inno Setup."""

import argparse
import ast
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

import build_exe
from generate_version_info import generate, read_metadata


DEPLOYMENT = Path(__file__).resolve().parents[1]
GENERATED = DEPLOYMENT / 'generated'
INSTALLER_SCRIPT = DEPLOYMENT / 'installer' / 'SelvamPOS.iss'
ROOT = DEPLOYMENT.parent
DEVELOPMENT = ROOT / 'Development'
PRODUCTION = ROOT / 'Production'
APP = PRODUCTION / 'dist' / 'SelvamPOS'
CONFIG = DEVELOPMENT / 'src' / 'config.py'


def find_compiler(explicit=None):
    requested = explicit or os.environ.get('ISCC_EXE')
    if requested:
        path = Path(requested).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f'Inno Setup compiler not found: {path}')
        return path
    found = shutil.which('ISCC.exe')
    if found:
        return Path(found).resolve()
    for variable in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
        base = os.environ.get(variable)
        if not base:
            continue
        for version in ('7', '6'):
            for folder in (Path(base), Path(base) / 'Programs'):
                path = folder / f'Inno Setup {version}' / 'ISCC.exe'
                if path.is_file():
                    return path.resolve()
    raise ValueError('Inno Setup ISCC.exe not found. Install Inno Setup or pass --iscc PATH. '
                     'See Deployment/README.md.')


def database_filename(config):
    tree = ast.parse(config.read_text(encoding='utf-8-sig'))
    assignments = [node.value for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'DATABASE_FILENAME'
                           for t in node.targets)]
    if len(assignments) != 1:
        raise ValueError('config.py must assign DATABASE_FILENAME exactly once')
    name = ast.literal_eval(assignments[0])
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.db', name):
        raise ValueError('DATABASE_FILENAME must be a simple .db filename without directories')
    return name


def validate_package(app, config):
    if not build_exe.production_mode(config):
        raise ValueError('Installer requires PRODUCTION_MODE = True; rebuild the executable')
    values, _ = read_metadata(config)
    try:
        metadata = json.loads((app / 'build_metadata.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ValueError('Missing or invalid build manifest; run Deployment/build_exe.bat') from exc
    if not isinstance(metadata, dict) or metadata.get('production_mode') is not True:
        raise ValueError('Installer rejects development packages; rebuild in production mode')
    if metadata.get('app_version') != values['APP_VERSION']:
        raise ValueError('Executable version differs from config.py; rebuild the executable')
    if metadata.get('source_sha256') != build_exe.source_digest():
        raise ValueError('Source/resources changed since the executable build; rebuild it')
    exe = app / 'SelvamPOS.exe'
    if not exe.is_file() or not (app / '_internal').is_dir():
        raise ValueError('Incomplete executable package; rebuild the executable')
    if metadata.get('executable_sha256') != hashlib.sha256(exe.read_bytes()).hexdigest():
        raise ValueError('Executable changed since the build; rebuild it')
    if metadata.get('package_sha256') != build_exe.package_digest(app):
        raise ValueError('Package contents changed or package fingerprint missing; rebuild it')
    return values['APP_VERSION'], metadata


def snapshot_database(source, destination):
    if not source.is_file():
        raise ValueError(f'Missing starter database: {source}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # SQLite backup includes committed WAL data and never creates an empty source DB.
    with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
        with closing(sqlite3.connect(destination)) as target:
            connection.backup(target)
            target.execute('PRAGMA journal_mode=DELETE')
            result = target.execute('PRAGMA quick_check').fetchall()
            if result != [('ok',)]:
                raise ValueError(f'Starter database integrity check failed: {result}')


def copy_runtime_data(source, destination):
    if not source.is_dir():
        raise ValueError(f'Missing starter runtime directory: {source}')
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.rglob('*')):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f'Starter data must not contain linked paths: {path}')
        relative = path.relative_to(source)
        if path.name == '.gitkeep' or '__pycache__' in relative.parts:
            continue
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def prepare_inputs():
    version, metadata = validate_package(APP, CONFIG)
    name = database_filename(CONFIG)
    guide = DEVELOPMENT / 'USERGUIDE.md'
    if not guide.is_file():
        raise ValueError(f'Missing user guide: {guide}')
    work = PRODUCTION / 'build'
    work.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='installer-', dir=work)).resolve()
    if not stage.is_relative_to(work.resolve()):
        raise ValueError('Installer staging directory escaped Production/build')
    shutil.copytree(APP, stage / 'app')
    if build_exe.package_digest(stage / 'app') != metadata['package_sha256']:
        raise ValueError('Executable package changed while staging; rebuild it')
    snapshot_database(DEVELOPMENT / 'db' / name, stage / 'seed' / 'db' / name)
    copy_runtime_data(DEVELOPMENT / 'runtime_data', stage / 'seed' / 'runtime_data')
    shutil.copy2(guide, stage / 'USERGUIDE.md')
    generate(CONFIG, GENERATED)
    shutil.copy2(GENERATED / 'version_info.iss', stage / 'version_info.iss')
    validate_package(APP, CONFIG)
    return stage, version, name


def compile_installer(compiler, script, stage, database, output):
    output.mkdir(parents=True, exist_ok=True)
    command = [str(compiler), '/Q',
               f'/DAppSource={stage / "app"}',
               f'/DSeedSource={stage / "seed"}',
               f'/DGuideSource={stage / "USERGUIDE.md"}',
               f'/DVersionInclude={stage / "version_info.iss"}',
               f'/DDatabaseFilename={database}',
               f'/DReleaseDir={output}', str(script)]
    subprocess.run(command, cwd=DEPLOYMENT, check=True)


def build(iscc=None):
    if sys.platform != 'win32':
        raise ValueError('Build the Windows installer on Windows')
    compiler = find_compiler(iscc)
    stage, version, name = prepare_inputs()
    print(f'Compiling SelvamPOS installer {version} with {compiler}', flush=True)
    compile_installer(compiler, INSTALLER_SCRIPT, stage, name, stage / 'output')
    artifact = stage / 'output' / f'SelvamPOS-Setup-{version}.exe'
    if not artifact.is_file():
        raise ValueError('Inno Setup did not produce the expected installer')
    validate_package(APP, CONFIG)
    release = PRODUCTION / 'release'
    release.mkdir(parents=True, exist_ok=True)
    target = release / artifact.name
    temporary = target.with_suffix('.exe.tmp')
    try:
        shutil.copy2(artifact, temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'Installer complete: {target}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iscc', type=Path, help='Full path to ISCC.exe (or set ISCC_EXE)')
    args = parser.parse_args(argv)
    try:
        build(args.iscc)
    except (OSError, ValueError, SyntaxError, sqlite3.Error, subprocess.CalledProcessError) as exc:
        print(f'Installer build failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
