"""Assert a frontend update cannot replace live state, configuration or backend."""
import contextlib
import importlib.util
import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('update_frontend', ROOT / 'tools/update_frontend.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class InstallerSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='weedverso-ui-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'app'
        self.root.mkdir()
        self.original = {'index.html': b'previous UI', 'assets/touch-ui.css': b'previous CSS', 'assets/touch-ui.js': b'previous JS',
                         'data/shared_state.json': b'{"balance":12345,"history":["keep"]}', '.env': b'unchanged test config', 'api_server.py': b'unchanged backend'}
        for relative, content in self.original.items():
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        self.archive = Path(self.temporary.name) / 'ui.zip'
        with zipfile.ZipFile(self.archive, 'w') as bundle:
            for relative in updater.FILES:
                bundle.write(ROOT / 'app' / relative, relative)

    def install(self):
        with patch('sys.argv', ['install_ui.py', str(self.root), str(self.archive)]), patch('os.chown', create=True), contextlib.redirect_stdout(io.StringIO()):
            exec(compile(updater.INSTALLER, '<ui-installer>', 'exec'), {})

    def assert_data_unchanged(self):
        for relative in ('data/shared_state.json', '.env', 'api_server.py'):
            self.assertEqual((self.root / relative).read_bytes(), self.original[relative])

    def test_updates_only_ui_and_keeps_a_private_backup_outside_public_directory(self):
        self.install()
        self.assert_data_unchanged()
        for relative in updater.FILES:
            self.assertEqual((self.root / relative).read_bytes(), (ROOT / 'app' / relative).read_bytes())
        backup = next((self.root.parent / 'ui-backups').iterdir())
        self.assertFalse(backup.is_relative_to(self.root))
        self.assertEqual((backup / 'shared_state.json').read_bytes(), self.original['data/shared_state.json'])
        self.assertEqual((backup / 'index.html').read_bytes(), self.original['index.html'])

    def test_rejects_a_package_containing_financial_data_before_changing_any_file(self):
        with zipfile.ZipFile(self.archive, 'a') as bundle:
            bundle.writestr('data/shared_state.json', 'must never be installed')
        with self.assertRaises(SystemExit):
            self.install()
        self.assert_data_unchanged()
        for relative in updater.FILES:
            self.assertEqual((self.root / relative).read_bytes(), self.original[relative])

    def test_failed_html_install_rolls_back_ui_and_leaves_data_intact(self):
        replace = os.replace

        def fail_html(source, target):
            if Path(target).name == 'index.html':
                raise OSError('simulated interrupted HTML update')
            return replace(source, target)

        with patch('os.replace', side_effect=fail_html), self.assertRaises(OSError):
            self.install()
        self.assert_data_unchanged()
        for relative in updater.FILES:
            self.assertEqual((self.root / relative).read_bytes(), self.original[relative])


if __name__ == '__main__':
    unittest.main()
