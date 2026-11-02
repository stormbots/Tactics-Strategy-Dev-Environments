import json
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path
from prepare_uat_version import ROOT, VERSIONS, prepare


class CandidateIdentity(unittest.TestCase):
    def test_pair_keeps_dependency_versions_and_baseline_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("package.json", "package-lock.json", "src-tauri/tauri.conf.json",
                         "src-tauri/Cargo.toml", "src-tauri/Cargo.lock"):
                dest = root / "installer" / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / "installer" / name, dest)
            baseline = root / "linux/lib/common.sh"
            baseline.parent.mkdir(parents=True)
            baseline.write_text('export SKYVIEW_VERSION="1.2.1"\n')
            before = tomllib.loads((root / "installer/src-tauri/Cargo.lock").read_text())["package"]
            npm_before = json.loads((root / "installer/package-lock.json").read_text())
            self.assertIn("1.2.19", VERSIONS)
            self.assertIn("1.2.20", VERSIONS)
            self.assertIn("1.2.21", VERSIONS)
            self.assertIn("1.2.22", VERSIONS)
            for version in VERSIONS:
                prepare(root, version)
                for name in ("package.json", "src-tauri/tauri.conf.json"):
                    self.assertEqual(json.loads((root / "installer" / name).read_text())["version"], version)
                lock = tomllib.loads((root / "installer/src-tauri/Cargo.lock").read_text())["package"]
                self.assertEqual([p for p in before if p["name"] != "skyview-dev-setup"],
                                 [p for p in lock if p["name"] != "skyview-dev-setup"])
                self.assertEqual(next(p["version"] for p in lock if p["name"] == "skyview-dev-setup"), version)
                self.assertEqual(baseline.read_text(), 'export SKYVIEW_VERSION="1.2.1"\n')
                npm = json.loads((root / "installer/package-lock.json").read_text())
                self.assertEqual(npm["packages"][""]["version"], version)
                self.assertEqual(npm["version"], version)
                self.assertEqual({k: v for k, v in npm["packages"].items() if k},
                                 {k: v for k, v in npm_before["packages"].items() if k})
            with self.assertRaises(ValueError):
                prepare(root, "1.2.23")

    def test_recovery_candidate_publishes_only_new_version_after_protected_checks(self):
        workflow = (ROOT / ".github/workflows/prepare-self-update-uat.yml").read_text()
        self.assertIn("BUILD_VERSIONS: 1.2.21 1.2.22\n", workflow)
        self.assertIn("CANDIDATE_VERSIONS: 1.2.22\n", workflow)
        self.assertNotIn("CANDIDATE_VERSIONS: 1.2.21", workflow)
        self.assertIn("CANDIDATE_NOTES: docs/RELEASE-NOTES-1.2.22.md", workflow)
        notes = (ROOT / "docs/RELEASE-NOTES-1.2.22.md").read_text()
        uat = (ROOT / "docs/RECOVERY-CLEAR-UAT-1.2.22.md").read_text()
        self.assertIn("There is nothing to recover from right now", notes)
        self.assertIn("Create support report", notes)
        self.assertIn("RECOVERY-CLEAR-UAT-1.2.22.md", notes)
        self.assertIn("**1.2.22**", uat)
        self.assertIn("git/matching-refs/tags/v1.2.22", workflow)
        self.assertIn("environment: sde-release-signing", workflow)
        self.assertIn("needs: [source, build-pair]", workflow)
        self.assertIn("Successful exact-main CI required", workflow)
        self.assertIn("--prerelease --latest=false", workflow)
        self.assertIn("SDE_UAT_PAIR_WINDOWS_OK", workflow)
        self.assertIn("SDE_UAT_PAIR_MINT_OK", workflow)
        release = (ROOT / ".github/workflows/build-dev-setup.yml").read_text()
        self.assertIn("'!v1.2.20'", release)
        self.assertIn("github.ref != 'refs/tags/v1.2.20'", release)
        self.assertIn("'!v1.2.21'", release)
        self.assertIn("github.ref != 'refs/tags/v1.2.21'", release)
        self.assertIn("'!v1.2.22'", release)
        self.assertIn("github.ref != 'refs/tags/v1.2.22'", release)

    def test_native_pair_probes_include_new_candidate_and_enabled_policy_checks(self):
        windows = (ROOT / "tests/Probe-NativeUpgrade.ps1").read_text()
        mint = (ROOT / "tests/Test-MintUatPairCI.sh").read_text()
        self.assertIn("1.2.22/Skyview-Dev-Setup-Windows-x64.exe", windows)
        self.assertIn("$versions = @('1.2.21', '1.2.22')", windows)
        self.assertEqual(windows.count("'1.2.19','1.2.20','1.2.21','1.2.22'"), 2)
        self.assertIn("1.2.22/Skyview-Dev-Setup-LinuxMint-amd64.deb", mint)
        self.assertIn("versions=(1.2.21 1.2.22)", mint)
        self.assertEqual(mint.count('"$version" == 1.2.21 || "$version" == 1.2.22'), 2)
