import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'generate_version_info.py'
spec = importlib.util.spec_from_file_location('generate_version_info', SCRIPT)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class VersionGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config.py'
        self.output = self.root / 'metadata'

    def write_config(self, version='1.2.3', company='Company', developer='Developer'):
        self.config.write_text(
            f'APP_VERSION = {version!r}\nCOMPANY_NAME = {company!r}\n'
            f'DEVELOPER_NAME = {developer!r}\n'
            "raise RuntimeError('must not execute configuration')\n",
            encoding='utf-8',
        )

    def test_metadata_is_generated_without_executing_config(self):
        self.write_config(company='Client company', developer='Dev\'s "quoted" POS')
        generator.generate(self.config, self.output)
        # Evaluate with constructor stubs to verify escaping and resource fields.
        constructors = ('VSVersionInfo', 'FixedFileInfo', 'StringFileInfo',
                        'StringTable', 'StringStruct', 'VarFileInfo', 'VarStruct')
        scope = {name: lambda *args, **kwargs: (args, kwargs) for name in constructors}
        strings = {}
        scope['StringStruct'] = lambda key, value: strings.update({key: value})
        resource = eval(compile((self.output / 'version_info.txt').read_text(encoding='utf-8'),
                               'version_info.txt', 'eval'), scope)
        self.assertEqual(resource[1]['ffi'][1]['filevers'], (1, 2, 3, 0))
        self.assertEqual(resource[1]['ffi'][1]['prodvers'], (1, 2, 3, 0))
        self.assertEqual(strings['FileVersion'], '1.2.3')
        self.assertEqual(strings['ProductVersion'], '1.2.3')
        self.assertEqual(strings['CompanyName'], 'Dev\'s "quoted" POS')
        self.assertEqual(strings['Comments'], 'Developed by Dev\'s "quoted" POS')
        installer = (self.output / 'version_info.iss').read_text(encoding='utf-8')
        self.assertIn('#define MyAppVersion "1.2.3"', installer)
        self.assertIn('#define MyAppPublisher "Dev\'s ""quoted"" POS"', installer)
        self.assertNotIn('Client company', installer)

    def test_invalid_versions_are_rejected_before_output(self):
        for version in ('1.2', '1.2.3.4', '01.2.3', '1.2.3-beta', '-1.2.3', '65536.0.0'):
            with self.subTest(version=version):
                self.write_config(version)
                with self.assertRaises(ValueError):
                    generator.generate(self.config, self.output)
                self.assertFalse(self.output.exists())

    def test_invalid_config_is_rejected(self):
        for source in ('APP_VERSION = "1.2.3"',
                       'APP_VERSION = str("1.2.3")',
                       'APP_VERSION = "1.2.3"\nAPP_VERSION = "2.0.0"'):
            self.config.write_text(source, encoding='utf-8')
            with self.assertRaises(ValueError):
                generator.generate(self.config, self.output)

    def test_client_company_is_not_required_for_publisher_metadata(self):
        self.config.write_text('APP_VERSION = "1.0.0"\nDEVELOPER_NAME = "SelvamPOS"\n')
        generator.generate(self.config, self.output)
        self.assertIn('#define MyAppPublisher "SelvamPOS"',
                      (self.output / 'version_info.iss').read_text(encoding='utf-8'))

    def test_cli_failure_is_nonzero_and_success_works_from_other_directory(self):
        self.write_config('invalid')
        args = [sys.executable, '-B', str(SCRIPT), '--config', str(self.config),
                '--output-dir', str(self.output)]
        failed = subprocess.run(args, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1)
        self.assertIn('generation failed', failed.stderr)
        self.write_config('65535.0.0')
        passed = subprocess.run(args, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(passed.returncode, 0, passed.stderr)


if __name__ == '__main__':
    unittest.main()
