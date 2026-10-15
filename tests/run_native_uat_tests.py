"""Run helper regressions; retain failures as GitHub annotations and local output."""
import os
from pathlib import Path
import subprocess
import sys

result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(Path(__file__).parent), "-p", "test_native_uat_fixtures.py", "-v"], capture_output=True, text=True)
output = result.stdout + result.stderr
print(output)
directory = Path(os.environ.get("SDE_FIXTURE_LOG_DIR", "evidence"))
directory.mkdir(exist_ok=True)
(directory / "unit-tests.txt").write_text(output, encoding="utf-8")
if result.returncode and os.environ.get("GITHUB_ACTIONS") == "true":
    message = output.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print("::error::" + message)
sys.exit(result.returncode)
