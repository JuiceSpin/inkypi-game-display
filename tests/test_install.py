import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'scripts/install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'InkyPi'
        interfaces={
            'plugins/plugin_registry.py':['register_plugin_blueprints','load_plugins','get_plugin_instance'],
            'blueprints/apikeys.py':['get_env_path','apikeys_page','save_apikeys'],
            'config.py':['load_env_key','get_config','get_resolution'],
            'refresh_task.py':['_determine_next_plugin','signal_config_change','manual_update']}
        for name,functions in interfaces.items():
            path=self.root/'src'/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('\n'.join(f'def {function}(*args): pass' for function in functions))
        (self.root/'src/inkypi.py').write_text('register_plugin_blueprints(app)\n')
        self.package=Path(self.tmp.name)/'release'
        self.source=self.package/'plugins/game_display';self.source.mkdir(parents=True)
        (self.source/'plugin-info.json').write_text(json.dumps({'id':'game_display','version':'0.1.0'}))
        (self.source/'game_display.py').write_text('VERSION="0.1.0"\n')
        state=self.root/'src/config/game_display';state.mkdir(parents=True)
        (state/'settings.json').write_text('preserve-settings')
        (self.root/'.env').write_text('preserve-native-keys')

    def tearDown(self):
        self.tmp.cleanup()

    def test_check_and_install_preserve_settings(self):
        self.assertEqual(installer.check(self.root),[])
        self.assertIsNone(installer.install(self.root,self.package,restart=False))
        self.assertEqual((self.root/'src/config/game_display/settings.json').read_text(),'preserve-settings')
        self.assertEqual((self.root/'.env').read_text(),'preserve-native-keys')
        self.assertEqual((self.root/'src/inkypi.py').read_text(),'register_plugin_blueprints(app)\n')

    def test_incompatible_install_is_unchanged(self):
        (self.root/'src/plugins/plugin_registry.py').write_text('def load_plugins(): pass\n')
        with self.assertRaises(ValueError):installer.install(self.root,self.package,restart=False)
        self.assertFalse((self.root/'src/plugins/game_display').exists())

    def test_update_backs_up_old_plugin(self):
        installer.install(self.root,self.package,restart=False)
        (self.root/'src/plugins/game_display/game_display.py').write_text('OLD=True\n')
        backup=installer.install(self.root,self.package,restart=False)
        self.assertEqual((backup/'game_display.py').read_text(),'OLD=True\n')

    def test_failed_copy_restores_previous_plugin(self):
        installer.install(self.root,self.package,restart=False)
        previous=self.root/'src/plugins/game_display/game_display.py';previous.write_text('OLD=True\n')
        original=shutil.copytree
        failed=False
        def failing(src,dst,*args,**kwargs):
            nonlocal failed
            if Path(dst)==previous.parent and not failed:
                failed=True;raise OSError('simulated install failure')
            return original(src,dst,*args,**kwargs)
        with patch.object(installer.shutil,'copytree',side_effect=failing):
            with self.assertRaises(OSError):installer.install(self.root,self.package,restart=False)
        self.assertEqual(previous.read_text(),'OLD=True\n')

    def test_failed_backup_keeps_working_plugin(self):
        installer.install(self.root,self.package,restart=False)
        previous=self.root/'src/plugins/game_display/game_display.py';previous.write_text('OLD=True\n')
        original=shutil.copytree
        def failing(src,dst,*args,**kwargs):
            if 'plugin-backups' in str(dst):raise OSError('backup failed')
            return original(src,dst,*args,**kwargs)
        with patch.object(installer.shutil,'copytree',side_effect=failing):
            with self.assertRaises(OSError):installer.install(self.root,self.package,restart=False)
        self.assertEqual(previous.read_text(),'OLD=True\n')
