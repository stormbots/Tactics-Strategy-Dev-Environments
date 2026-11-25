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
        for name in ('common.sh', 'coordination.sh', 'coordination.py', 'project_location.py', 'editor_location.py'):
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
        foreign = fixture / 'foreign-repository'
        subprocess.run(['/usr/bin/git', 'init', '-q', str(foreign)], check=True, capture_output=True)
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
        run('/usr/bin/git', 'config', '--global', 'init.defaultBranch', 'student-choice')
        run('/usr/bin/git', 'config', '--global', 'fetch.prune', 'no')
        gitconfig = home / '.gitconfig'
        before_git = gitconfig.read_bytes()
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
            assert gitconfig.read_bytes() == before_git
            assert settings.read_bytes() == before_settings
            assert json.loads(settings.read_text()) == json.loads(initial)
            assert not (ROOT / 'transaction.json').exists()
            if attempt == 0:
                assert not list(settings.parent.glob('settings.json.pre-skyview-v*.bak'))
        # JSONC comments and existing bytes survive without a settings writer.
        jsonc = '// retained comment\n{"editor.fontSize":21}\n'
        run('/usr/bin/python3', '-c', 'import pathlib,sys;pathlib.Path(sys.argv[1]).write_text(sys.argv[2])', str(settings), jsonc)
        result = run('/bin/bash', str(script))
        assert settings.read_bytes() == jsonc.encode()
        assert 'preferences are preserved' in result.stdout + result.stderr
        assert project.read_bytes() == before_project
        assert gitconfig.read_bytes() == before_git
        for missing in (False, True):
            run('/usr/bin/python3', '-c', 'import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.unlink() if sys.argv[2] == "missing" else p.write_bytes(b"")', str(settings), 'missing' if missing else 'empty')
            run('/bin/bash', str(script))
            if missing:
                assert not settings.exists()
            else:
                assert settings.read_bytes() == b''
            assert project.read_bytes() == before_project
            assert gitconfig.read_bytes() == before_git
        for key, expected in [('user.name', 'Synthetic Student'), ('user.email', 'student@example.invalid'),
                              ('init.defaultBranch', 'student-choice'), ('fetch.prune', 'no')]:
            assert run('/usr/bin/git', 'config', '--global', key).stdout.strip() == expected
        assert gitconfig.read_bytes() == before_git
        unset = subprocess.run(['/usr/bin/git', 'config', '--global', '--get', 'pull.ff'], cwd=home,
                               env=env, preexec_fn=student, capture_output=True)
        assert unset.returncode == 1 and unset.stdout == b''
        source = home / 'worktree source'
        linked = home / 'linked worktree'
        run('/usr/bin/git', 'init', '-q', str(source))
        run('/usr/bin/git', '-C', str(source), '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture', '--allow-empty')
        run('/usr/bin/git', '-C', str(source), 'worktree', 'add', '-qb', 'student-worktree', str(linked))
        run('/usr/bin/python3', '-c', 'import pathlib,sys;pathlib.Path(sys.argv[1]).write_text("keep student work")', str(linked / 'uncommitted.txt'))
        before_config = (source / '.git/config').read_bytes()
        before_dirty = (linked / 'uncommitted.txt').read_bytes()
        helper = fixture / 'lib/project_location.py'
        for path in (source, linked):
            value = json.loads(run('/usr/bin/python3', str(helper), '--json', str(path)).stdout)
            assert value['status'] == 'verified', value
        refused = json.loads(run('/usr/bin/python3', str(helper), '--json', str(foreign)).stdout)
        assert refused['status'] == 'incomplete', 'Git ownership/trust refusal was bypassed'
        assert (source / '.git/config').read_bytes() == before_config
        assert (linked / 'uncommitted.txt').read_bytes() == before_dirty
        assert gitconfig.read_bytes() == before_git
        print('SDE_PROJECT_WORKTREE_STANDARD_USER_LINUX_OK')
        assert not (ROOT / 'transaction.json').exists()
    print('SDE_PROFILE_PRESERVATION_LINUX_OK: real non-root profile; project/Git bytes, strict JSON/JSONC, empty and absent settings retained')


if __name__ == '__main__':
    main()
