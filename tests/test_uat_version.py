import json
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path
from prepare_uat_version import ROOT, prepare


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
            for version in ("1.2.2", "1.2.3", "1.2.4", "1.2.5", "1.2.6", "1.2.7", "1.2.8"):
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
            with self.assertRaises(ValueError):
                prepare(root, "1.2.9")
