"""Compatibilidade e regressões; APIs do Windows simuladas, sem modificar o PC."""
import ctypes
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import gaming
import history
import main
import network_lab
import optimizations
import performance_lab
from game_preparation import GamePreparation


class CompatibilityTests(unittest.TestCase):
    def test_windows_64_bit_window_handle_is_preserved(self):
        handle = 2**40 + 7
        process = Mock()
        process.name.return_value = 'editor.exe'
        process.create_time.return_value = 123
        process.username.return_value = 'user'
        process.exe.return_value = '/apps/editor.exe'
        process.is_running.return_value = True
        def enumerate_windows(callback, parameter):
            callback(handle, parameter)
            return True
        def window_pid(hwnd, pointer):
            pointer._obj.value = 999999
            return 1
        user32 = SimpleNamespace(EnumWindows=Mock(side_effect=enumerate_windows),
                                 GetWindowThreadProcessId=Mock(side_effect=window_pid),
                                 PostMessageW=Mock(return_value=1))
        factory = getattr(ctypes, 'WINFUNCTYPE', ctypes.CFUNCTYPE)
        with patch.object(main, 'IS_WINDOWS', True), patch.object(main.psutil, 'Process', return_value=process), patch.object(ctypes, 'windll', SimpleNamespace(user32=user32), create=True), patch.object(ctypes, 'WINFUNCTYPE', factory, create=True):
            result = main.terminate_user_process(999999, 'editor.exe', 123)
        self.assertTrue(result['success'])
        self.assertEqual(user32.PostMessageW.call_args.args[0], handle)
        self.assertEqual(ctypes.sizeof(user32.PostMessageW.argtypes[0]), ctypes.sizeof(ctypes.c_void_p))
        process.terminate.assert_not_called()

    def test_nan_process_timestamp_cannot_bypass_identity_check(self):
        process = Mock(); process.name.return_value = 'editor.exe'; process.create_time.return_value = 123
        with patch.object(main.psutil, 'Process', return_value=process):
            self.assertFalse(main.terminate_user_process(999999, 'editor.exe', float('nan'))['success'])
        process.terminate.assert_not_called()

    def test_unreachable_windows_ping_is_not_a_success(self):
        result = SimpleNamespace(returncode=0, stdout='Reply from 192.168.1.1: Destination host unreachable.', stderr='')
        with patch.object(network_lab, 'os', SimpleNamespace(name='nt')), patch.object(network_lab.shutil, 'which', return_value='ping'), patch.object(network_lab.subprocess, 'run', return_value=result):
            probe = network_lab._ping_once('192.0.2.1')
        self.assertFalse(probe['success'])
        self.assertIsNone(probe['latency_ms'])

    def test_windows_echo_response_remains_successful(self):
        result = SimpleNamespace(returncode=0, stdout='Resposta de 192.168.1.1: bytes=32 tempo<1ms TTL=64', stderr='')
        with patch.object(network_lab, 'os', SimpleNamespace(name='nt')), patch.object(network_lab.shutil, 'which', return_value='ping'), patch.object(network_lab.subprocess, 'run', return_value=result):
            probe = network_lab._ping_once('192.168.1.1')
        self.assertTrue(probe['success']); self.assertTrue(probe['below_resolution'])

    def test_damaged_startup_backup_blocks_modifications(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'backup.json'; path.write_bytes(b'\xff\xfeinvalid')
            with patch.object(optimizations, '_startup_backup_path', return_value=path), patch.object(optimizations, 'os', SimpleNamespace(name='nt')), patch.dict('sys.modules', {'winreg': SimpleNamespace()}):
                self.assertFalse(optimizations.startup_overview()['supported'])
                self.assertFalse(optimizations.set_startup_enabled('App', False)['success'])
            self.assertEqual(path.read_bytes(), b'\xff\xfeinvalid')

    def test_corrupt_history_entries_do_not_break_dashboard(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'history.json'
            path.write_text(json.dumps({'diagnostics':[None, 5, {'timestamp':1}], 'actions':[None, {'timestamp':'bad'}, {'timestamp':2}]}))
            result = history.get_history(path)
            self.assertEqual(len(result['diagnostics']), 1)
            self.assertEqual(len(result['actions']), 1)
            path.write_bytes(b'\xff')
            self.assertEqual(history.get_history(path)['actions'], [])

    def test_invalid_performance_records_are_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'history.json'
            path.write_text(json.dumps({'records':[None, {'system':None}, {'system':{}, 'capture':{}}]}))
            self.assertEqual(len(performance_lab.load_history(path)), 1)
            path.write_bytes(b'\xff')
            self.assertEqual(performance_lab.load_history(path), [])

    def test_epic_invalid_manifest_is_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Epic/EpicGamesLauncher/Data/Manifests'; path.mkdir(parents=True)
            (path / 'broken.item').write_text('[]')
            (path / 'bad.item').write_text('{"DisplayName":123,"AppName":45,"InstallLocation":12}')
            with patch.object(gaming, 'os', SimpleNamespace(name='nt', environ={'ProgramData':folder})):
                self.assertEqual(gaming._epic_games(), [])

    def test_invalid_game_session_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'game_session.json'
            path.write_text('{"active":true,"previous_guid":null}')
            self.assertFalse(GamePreparation(folder).restore()['success'])
            self.assertTrue(path.exists())

    def test_missing_webview_runtime_is_reported(self):
        import app_webview
        window = Mock()
        fake = SimpleNamespace(create_window=Mock(return_value=window), start=Mock(side_effect=RuntimeError('WebView2 absent')))
        user32 = SimpleNamespace(MessageBoxW=Mock())
        with patch.dict('sys.modules', {'webview':fake}), patch.object(app_webview.sys, 'platform', 'win32'), patch.object(app_webview, 'install_exception_logging'), patch.object(app_webview, 'log_error') as log, patch.object(app_webview, 'WindowLifecycle'), patch.object(ctypes, 'windll', SimpleNamespace(user32=user32), create=True):
            app_webview.launch_gui()
        log.assert_called_once(); user32.MessageBoxW.assert_called_once()


if __name__ == '__main__': unittest.main()
