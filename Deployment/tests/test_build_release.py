import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'build_release.bat'


@unittest.skipUnless(sys.platform == 'win32', 'Windows batch workflow')
class CombinedReleaseTests(unittest.TestCase):
    def run_workflow(self, executable_code=0, installer_code=0, arguments=()):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deployment = root / 'release scripts with spaces'
            deployment.mkdir()
            unrelated = root / 'another working directory'
            unrelated.mkdir()
            script = deployment / SCRIPT.name
            shutil.copyfile(SCRIPT, script)
            for name, stage, code in (('build_exe.bat', 'exe', executable_code),
                                      ('build_installer.bat', 'installer', installer_code)):
                (deployment / name).write_text(
                    '@echo off\n'
                    f'>>"%~dp0calls.txt" echo {stage}\n'
                    f'>>"%~dp0arguments.txt" echo {stage} %*\n'
                    f'exit /b {code}\n', encoding='utf-8')
            # cmd /s /c requires an outer quote pair around the full command,
            # in addition to quotes around a batch path containing spaces.
            args = ''.join(f' "{arg}"' for arg in arguments)
            command = f'"{os.environ["COMSPEC"]}" /d /s /c ""{script}"{args}"'
            result = subprocess.run(command, cwd=unrelated, capture_output=True, text=True)
            calls = deployment / 'calls.txt'
            passed = deployment / 'arguments.txt'
            return (result, calls.read_text().splitlines() if calls.exists() else [],
                    passed.read_text() if passed.exists() else '')

    def test_executable_failure_skips_installer_and_preserves_exit_code(self):
        result, calls, _ = self.run_workflow(executable_code=17)
        self.assertEqual(result.returncode, 17, result.stdout + result.stderr)
        self.assertEqual(calls, ['exe'])
        self.assertNotIn('Release complete.', result.stdout)

    def test_installer_failure_is_returned(self):
        result, calls, _ = self.run_workflow(installer_code=23)
        self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
        self.assertEqual(calls, ['exe', 'installer'])
        self.assertNotIn('Release complete.', result.stdout)

    def test_success_and_installer_argument_forwarding(self):
        compiler = r'C:\Tools With Spaces\Inno Setup\ISCC.exe'
        result, calls, arguments = self.run_workflow(arguments=('--iscc', compiler))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls, ['exe', 'installer'])
        self.assertIn('Release complete.', result.stdout)
        exe_args, installer_args = arguments.splitlines()
        self.assertEqual(exe_args.strip(), 'exe')
        self.assertIn('--iscc', installer_args)
        self.assertIn(compiler, installer_args)

    def test_help_does_not_start_builds(self):
        result, calls, _ = self.run_workflow(arguments=('--help',))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls, [])
        self.assertIn('Usage:', result.stdout)


if __name__ == '__main__':
    unittest.main()
