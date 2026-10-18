"""Reviewed future local launcher; never execute during mocked CI.

Prevent permissive checkout creation by setting umask before the listener.
No chmod/chown, registration, download, service, package or retry operations.
"""
import grp
import json
import os
from pathlib import Path
import pwd
import stat
import sys

SESSION = 'mint-prep-runner-private-session'
WORK = '_work-private'
ORG = 'https://github.com/stormbots'
LIMIT = 16 * 1024


class Stop(Exception):
    pass


def require(ok, reason):
    if not ok:
        raise Stop(reason)


def read_settings(path, uid):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == uid and
                stat.S_IMODE(before.st_mode) == 0o600 and before.st_nlink == 1 and
                0 < before.st_size <= LIMIT, 'SETTINGS_OWNER')
        data = os.read(fd, LIMIT + 1)
        after = os.fstat(fd)
        require(len(data) == before.st_size and
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                'SETTINGS_CHANGED')
        def unique(pairs):
            result = {}
            for name, value in pairs:
                require(name not in result, 'SETTINGS_DUPLICATE')
                result[name] = value
            return result
        result = json.loads(data, object_pairs_hook=unique)
        require(type(result) is dict, 'SETTINGS_FORMAT')
        return result
    finally:
        try:
            os.close(fd)
        except OSError:
            raise Stop('SETTINGS_CLEANUP_UNCERTAIN') from None


def inspect_runner(home, uid, *, reader=read_settings):
    home = Path(home)
    require(home.is_absolute() and '..' not in home.parts, 'HOME_PATH')
    session = home / SESSION
    # Check each ancestor without following symlinks; no permissions are repaired.
    for path in reversed((session, *session.parents)):
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid in {0, uid} and
                not stat.S_IMODE(info.st_mode) & 0o022, 'SESSION_ANCESTRY')
    for path in (session, session / WORK):
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == uid and
                stat.S_IMODE(info.st_mode) == 0o700, 'PRIVATE_DIRECTORY')
        # Inherited default ACLs can override umask for newly created children.
        # Reject them; never remove ACLs or install an ACL utility automatically.
        require('system.posix_acl_default' not in os.listxattr(path, follow_symlinks=False),
                'DEFAULT_ACL')
    with os.scandir(session / WORK) as entries:
        require(next(entries, None) is None, 'WORK_NOT_EMPTY')
    settings = reader(session / '.runner', uid)
    require(settings.get('workFolder') == WORK and settings.get('ephemeral') is True and
            settings.get('agentName') == 'sde-mint-prep-once' and
            settings.get('gitHubUrl') == ORG, 'RUNNER_SETTINGS')
    script = session / 'run.sh'
    info = script.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == uid and info.st_nlink == 1 and
            stat.S_IMODE(info.st_mode) & 0o100 and not stat.S_IMODE(info.st_mode) & 0o022,
            'RUNNER_SCRIPT')
    return session


def main():
    old_mask = None
    try:
        require(len(sys.argv) == 1, 'NO_ARGUMENTS')
        uid = os.getuid()
        who = pwd.getpwuid(uid)
        require(uid >= 1000 and os.geteuid() == uid and who.pw_name == 'sde-runner', 'ACCOUNT')
        groups = {grp.getgrgid(g).gr_name for g in set(os.getgroups()) | {os.getgid()}}
        require(not groups & {'root','sudo','admin','docker','lxd','libvirt'}, 'GROUPS')
        old_mask = os.umask(0o077)
        session = inspect_runner(who.pw_dir, uid)
        os.chdir(session)
        # exec retains the mask for run.sh, listener, worker, checkout and git.
        # It never returns on success. No user-supplied command or arguments.
        os.execv(str(session / 'run.sh'), [str(session / 'run.sh')])
        raise Stop('EXEC_RETURNED')
    except Exception as error:
        reason = str(error) if isinstance(error, Stop) else 'LAUNCH_STOPPED'
        print(json.dumps({'started': False, 'reason': reason, 'retryAuthorized': False}))
        return 1
    finally:
        if old_mask is not None:
            os.umask(old_mask)


if __name__ == '__main__':
    raise SystemExit(main())
