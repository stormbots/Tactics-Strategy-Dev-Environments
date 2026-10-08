"""Read-only regression checks for the provisioning safety contract."""
from pathlib import Path
import re, unittest
ROOT=Path(__file__).resolve().parents[1]
class Backends(unittest.TestCase):
    def text(self,p): return (ROOT/p).read_text(encoding='utf-8-sig')
    def test_canonical_extensions_match(self):
        self.assertEqual(self.text('linux/extensions.txt').splitlines(),self.text('windows/chocolatey/tools/extensions.txt').splitlines())
    def test_linux_user_boundary(self):
        user=self.text('linux/Configure-SkyviewUser.sh')
        self.assertNotRegex(user,r'\bsudo\b')
        self.assertIn('must not run as root',user)
        install=self.text('linux/Install-SkyviewStudentDev.sh')
        self.assertIn('"$SYSTEM_ONLY" != 1',install)
        self.assertNotIn('/usr/bin/python3 ',install)
        update=self.text('linux/Update-SkyviewStudentDev.sh')
        self.assertNotRegex(update,r'apt-get\s+(dist-upgrade|upgrade|full-upgrade)')
        self.assertIn('"nodejs=$NODE_VERSION"',update)
        self.assertNotIn('install_codium_extensions_for_user',update)
    def test_no_identity_provisioning(self):
        for p in ['linux/Configure-SkyviewUser.sh','windows/chocolatey/tools/Configure-SkyviewUser.ps1']:
            self.assertNotRegex(self.text(p),r'git config[^\n]*(user\.name|user\.email)')
            self.assertNotIn('gh auth login',self.text(p))
    def test_privileged_interface(self):
        rust=self.text('installer/src-tauri/src/process.rs')
        self.assertIn('["install","repair","update"]',re.sub(r'\s+', '', rust))
        self.assertIn('parse_str(session)',rust)
        self.assertIn('debug_assertions',rust)
        self.assertIn('env_clear()',rust)
        cap=self.text('installer/src-tauri/capabilities/main.json')
        self.assertNotIn('shell:',cap)
        self.assertNotIn('fs:',cap)
    def test_release_gate(self):
        workflow=self.text('.github/workflows/build-dev-setup.yml')
        self.assertIn('needs: [checks, native]',workflow)
        self.assertIn('--verify-tag --prerelease',workflow)
        self.assertIn('sha256sum --check',workflow)
        fallback=self.text('.github/workflows/publish-linux-v1.0.1.yml')
        self.assertIn('ref: linux-v1.0.1',fallback)
        self.assertNotIn('--clobber',fallback)
    def test_metadata_helpers_are_persisted(self):
        windows=self.text('windows/chocolatey/tools/chocolateyInstall.ps1')
        self.assertIn("'ToolRecords.ps1'",windows)
        self.assertIn("'Inspect-SkyviewSchedule.ps1'",windows)
        self.assertIn('"$SKYVIEW_LIB/tool_records.py"',self.text('linux/Install-SkyviewStudentDev.sh'))
if __name__=='__main__': unittest.main()
