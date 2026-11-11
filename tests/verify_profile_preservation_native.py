"""Real Linux profile script on a disposable installed native CI host/Mint.

Controlled empty extension list: no extension/network installation is claimed.
Real coordination, Bash, Git, jq, user identity and filesystem are exercised.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path('/var/lib/skyview-robotics-coordination')


def main(backend=None):
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.geteuid() != 0:
        raise RuntimeError('Disposable root GitHub runner required.')
    if backend is None:
        backend = Path('/usr/lib/Skyview Dev Setup/backend/linux')
    # Do not replace a native journal, deployed repository policy or owner data.
    assert not (ROOT / 'transaction.json').exists()
    assert not Path('/etc/skyview-robotics/student-dev/repositories.csv').exists()
    assert shutil.which('git') and shutil.which('jq'), 'Git/jq fixture dependencies required'
    with tempfile.TemporaryDirectory(prefix='sde-profile-ci-', dir='/var/lib') as directory:
        fixture = Path(directory)
        fixture.chmod(0o755)
        (fixture / 'lib').mkdir()
        (fixture / 'config').mkdir()
        for name in ('common.sh', 'coordination.sh', 'coordination.py'):
            shutil.copyfile(backend / 'lib' / name, fixture / 'lib' / name)
        script = fixture / 'Configure-SkyviewUser.sh'
        shutil.copyfile(backend / script.name, script)
        assert script.read_bytes() == (backend / script.name).read_bytes()
        shutil.copyfile(backend / 'config/codium-settings.json', fixture / 'config/codium-settings.json')
        (fixture / 'extensions.txt').write_text('# Controlled empty extension fixture\n')
        (fixture / 'repositories.csv').write_text('name,url,branch,enabled\nexisting,https://example.invalid/sde-profile.git,,true\n')
        (fixture / 'bin').mkdir()
        # Presence check only; any unexpected extension execution must fail.
        (fixture / 'bin/codium').symlink_to('/usr/bin/false')
        home = fixture / 'home'
        home.mkdir()
        os.chown(home, 65534, 65534)
        home.chmod(0o700)
        env = {'HOME': str(home), 'USER': 'nobody', 'LOGNAME': 'nobody',
               'PATH': f'{fixture / "bin"}:/usr/bin:/bin', 'LANG': 'C.UTF-8'}

        def student():
            os.setgroups([])
            os.setgid(65534)
            os.setuid(65534)

        def run(*args):
            return subprocess.run(args, cwd=home, env=env, preexec_fn=student,
                                  check=True, capture_output=True, text=True)

        run('/usr/bin/git', 'config', '--global', 'user.name', 'Synthetic Student')
        run('/usr/bin/git', 'config', '--global', 'user.email', 'student@example.invalid')
        # All fixture data is created by the real non-root account.
        run('/bin/bash', '-c', 'mkdir -p "$HOME/Development/existing" "$HOME/.config/VSCodium/User"; printf "student-project-bytes\\n" > "$HOME/Development/existing/project.txt"')
        project = home / 'Development/existing/project.txt'
        before_project = project.read_bytes()
        settings = home / '.config/VSCodium/User/settings.json'
        # Write through the account to retain its ownership.
        initial = '{"editor.fontSize":19,"editor.formatOnSave":false,"sde.fixture":"keep-user-value"}\n'
        run('/usr/bin/python3', '-c', 'import pathlib,sys;pathlib.Path(sys.argv[1]).write_text(sys.argv[2])', str(settings), initial)
        before_settings = settings.read_bytes()
        for attempt in range(2):  # Same profile phase used after Install and Repair.
            output = run('/bin/bash', str(script)).stdout
            assert 'User configuration complete' in output
            assert project.read_bytes() == before_project
            result = json.loads(settings.read_text())
            assert result['editor.fontSize'] == 19 and result['sde.fixture'] == 'keep-user-value'
            baseline = json.loads((fixture / 'config/codium-settings.json').read_text())
            for key, value in baseline.items():
                assert result[key] == json.loads(initial).get(key, value)
            assert not (ROOT / 'transaction.json').exists()
            if attempt == 0:
                backups = list(settings.parent.glob('settings.json.pre-skyview-v*.bak'))
                assert len(backups) == 1 and backups[0].read_bytes() == before_settings
        # Existing JSONC cannot be safely merged: original bytes must survive.
        jsonc = '// retained comment\n{"editor.fontSize":21}\n'
        run('/usr/bin/python3', '-c', 'import pathlib,sys;pathlib.Path(sys.argv[1]).write_text(sys.argv[2])', str(settings), jsonc)
        result = run('/bin/bash', str(script))
        assert settings.read_bytes() == jsonc.encode()
        assert 'preserved unchanged' in result.stdout + result.stderr
        assert project.read_bytes() == before_project
        for key, expected in [('user.name', 'Synthetic Student'), ('user.email', 'student@example.invalid'),
                              ('init.defaultBranch', 'main'), ('fetch.prune', 'true'), ('pull.ff', 'only')]:
            assert run('/usr/bin/git', 'config', '--global', key).stdout.strip() == expected
        assert not (ROOT / 'transaction.json').exists()
    print('SDE_PROFILE_PRESERVATION_LINUX_OK: real non-root profile phase twice, projects/user choices/JSONC retained; disclosed Git defaults applied')


if __name__ == '__main__':
    main()
