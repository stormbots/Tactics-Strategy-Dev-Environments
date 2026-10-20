"""Read-only preflight boundaries; never change the host's package state."""
import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
spec=importlib.util.spec_from_file_location('preflight',Path(__file__).resolve().parents[1]/'linux/lib/update_preflight.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Preflight(unittest.TestCase):
    def test_disk_threshold_and_unavailable_are_distinct(self):
        with patch.object(m.shutil,'disk_usage',return_value=Mock(free=100)):
            self.assertEqual(m.disk('/',200,'System')['status'],'blocking')
        with patch.object(m.shutil,'disk_usage',side_effect=OSError):
            self.assertEqual(m.disk('/',200,'System')['status'],'unavailable')
    def test_held_lock_blocks_and_is_not_deleted(self):
        stat=Mock(st_dev=0x801,st_ino=123)
        with patch.object(m.os,'stat',return_value=stat),patch.object(Path,'read_text',return_value='1: POSIX ADVISORY WRITE 1234 08:01:123 0 EOF'):
            self.assertEqual(m.package_state()['status'],'blocking')
    def test_dpkg_audit_problem_blocks(self):
        with patch.object(m.os,'stat',side_effect=FileNotFoundError),patch.object(Path,'read_text',return_value=''),patch.object(m.subprocess,'run',return_value=Mock(returncode=0,stdout=b'pending configuration')) as run:
            self.assertEqual(m.package_state()['status'],'blocking')
            self.assertEqual(run.call_args.args[0],['/usr/bin/dpkg','--audit'])
    def test_failed_probe_is_unknown_not_pass(self):
        with patch.object(m.urllib.request,'urlopen',side_effect=OSError('secret raw response')):
            row=m.connectivity(('Package source','https://example.invalid'))
            self.assertEqual(row['status'],'unavailable');self.assertNotIn('secret',row['detail'])
