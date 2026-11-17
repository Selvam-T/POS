import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_installer as installer


class InstallerBuildTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / 'src'
        self.source.mkdir()
        self.config = self.source / 'config.py'
        self.config.write_text('APP_VERSION = "1.2.3"\nDEVELOPER_NAME = "Developer"\n'
                               'PRODUCTION_MODE = True\nDATABASE_FILENAME = "Starter.db"\n')
        self.app = self.root / 'app'
        (self.app / '_internal').mkdir(parents=True)
        self.exe = self.app / 'SelvamPOS.exe'
        self.exe.write_bytes(b'executable')
        self.library = self.app / '_internal' / 'library.dll'
        self.library.write_bytes(b'library')
        patcher = patch.object(installer.build_exe, 'SOURCE', self.source)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.metadata = {
            'app_version': '1.2.3', 'production_mode': True,
            'source_sha256': installer.build_exe.source_digest(),
            'executable_sha256': hashlib.sha256(self.exe.read_bytes()).hexdigest(),
            'package_sha256': installer.build_exe.package_digest(self.app),
        }
        self.write_manifest()

    def write_manifest(self):
        (self.app / 'build_metadata.json').write_text(json.dumps(self.metadata))

    def test_matching_production_package_is_accepted(self):
        version, _ = installer.validate_package(self.app, self.config)
        self.assertEqual(version, '1.2.3')
        self.assertEqual(installer.database_filename(self.config), 'Starter.db')

    def test_development_wrong_version_and_old_manifests_are_rejected(self):
        for change in ({'production_mode': False}, {'app_version': '1.2.2'},
                       {'package_sha256': None}, {'source_sha256': 'stale'}):
            with self.subTest(change=change):
                original = self.metadata.copy()
                self.metadata.update(change)
                self.write_manifest()
                with self.assertRaises(ValueError):
                    installer.validate_package(self.app, self.config)
                self.metadata = original

    def test_changed_executable_or_internal_library_is_rejected(self):
        for path in (self.exe, self.library):
            original = path.read_bytes()
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                installer.validate_package(self.app, self.config)
            path.write_bytes(original)

    def test_changed_source_and_missing_manifest_are_rejected(self):
        self.config.write_text(self.config.read_text() + '# changed\n')
        with self.assertRaises(ValueError):
            installer.validate_package(self.app, self.config)
        (self.app / 'build_metadata.json').unlink()
        with self.assertRaises(ValueError):
            installer.validate_package(self.app, self.config)

    def test_database_snapshot_contains_committed_wal_transactions(self):
        source = self.root / 'live.db'
        destination = self.root / 'seed' / 'snapshot.db'
        with closing(sqlite3.connect(source)) as connection:
            connection.execute('PRAGMA journal_mode=WAL')
            connection.execute('PRAGMA wal_autocheckpoint=0')
            connection.execute('CREATE TABLE example (value TEXT)')
            connection.execute("INSERT INTO example VALUES ('committed')")
            connection.commit()
            self.assertGreater(Path(str(source) + '-wal').stat().st_size, 0)
            installer.snapshot_database(source, destination)
        with closing(sqlite3.connect(destination)) as snapshot:
            self.assertEqual(snapshot.execute('SELECT value FROM example').fetchone(), ('committed',))
        self.assertFalse(Path(str(destination) + '-wal').exists())
        self.assertFalse(Path(str(destination) + '-shm').exists())

    def test_missing_database_does_not_create_empty_source(self):
        source = self.root / 'missing.db'
        with self.assertRaises(ValueError):
            installer.snapshot_database(source, self.root / 'snapshot.db')
        self.assertFalse(source.exists())

    def test_runtime_staging_preserves_nested_files_and_excludes_placeholders(self):
        source = self.root / 'runtime'
        (source / 'json' / 'nested').mkdir(parents=True)
        (source / '.gitkeep').write_bytes(b'')
        (source / 'json' / '.gitkeep').write_bytes(b'')
        (source / 'json' / 'nested' / 'settings.json').write_bytes(b'{}')
        destination = self.root / 'seed'
        installer.copy_runtime_data(source, destination)
        self.assertEqual((destination / 'json' / 'nested' / 'settings.json').read_bytes(), b'{}')
        self.assertEqual(list(destination.rglob('.gitkeep')), [])

    def test_invalid_database_filename_and_compiler_fail_clearly(self):
        self.config.write_text('DATABASE_FILENAME = "../escape.db"')
        with self.assertRaises(ValueError):
            installer.database_filename(self.config)
        with self.assertRaises(ValueError):
            installer.find_compiler(self.root / 'missing-iscc.exe')


if __name__ == '__main__':
    unittest.main()
