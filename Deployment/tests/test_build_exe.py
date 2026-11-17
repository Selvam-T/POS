import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('build_exe', SCRIPTS / 'build_exe.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildModeTests(unittest.TestCase):
    def test_metadata_failure_stops_before_pyinstaller(self):
        with patch.object(builder.sys, 'platform', 'win32'), \
                patch.object(builder.sys, 'version_info', (3, 12, 10)), \
                patch.object(builder, 'validate_mode', return_value=True), \
                patch.object(builder.importlib.util, 'find_spec', return_value=object()), \
                patch.object(builder, 'generate', side_effect=ValueError('invalid metadata')), \
                patch.object(builder.subprocess, 'run') as package:
            with self.assertRaisesRegex(ValueError, 'invalid metadata'):
                builder.build()
            package.assert_not_called()

    def test_mode_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.py'
            for mode in (False, True):
                config.write_text(f'PRODUCTION_MODE = {mode}\nraise RuntimeError()')
                self.assertEqual(builder.validate_mode(config, development=not mode), mode)
                with self.assertRaises(ValueError):
                    builder.validate_mode(config, development=mode)
            for source in ('PRODUCTION_MODE = "False"', 'PRODUCTION_MODE = 1',
                           'PRODUCTION_MODE = bool(1)', 'OTHER = False',
                           'PRODUCTION_MODE = True\nPRODUCTION_MODE = False'):
                config.write_text(source)
                with self.assertRaises(ValueError):
                    builder.production_mode(config)

    def test_fingerprint_excludes_tests_but_includes_resources_and_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'assets').mkdir()
            config = root / 'config.py'
            config.write_text('PRODUCTION_MODE = True')
            with patch.object(builder, 'SOURCE', root):
                original = builder.source_digest()
                (root / 'tests' / 'test_example.py').write_text('pass')
                self.assertEqual(original, builder.source_digest())
                (root / 'assets' / 'logo.png').write_bytes(b'image')
                resource_change = builder.source_digest()
                self.assertNotEqual(original, resource_change)
                config.write_text('PRODUCTION_MODE = False')
                self.assertNotEqual(resource_change, builder.source_digest())


if __name__ == '__main__':
    unittest.main()
