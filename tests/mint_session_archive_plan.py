"""Pure archival/setup plan validator. No host inspector, executor or CLI.

Observations must come from a separately authorized, reviewed host procedure.
Passing synthetic/local checks is not native ownership or quiescence proof.
"""
HOME = '/home/sde-runner'
SOURCE = HOME + '/mint-prep-runner-private-session'
LEGACY = HOME + '/mint-prep-runner-session'
ARCHIVE = HOME + '/mint-prep-runner-private-session-checkout-39132131036'
WORK = SOURCE + '/_work-private'
IDENTITY = (66306, 12088154)  # owner-supplied successful observer evidence
REASON = 'SESSION_ARCHIVE_STOP'


class Stop(Exception):
    pass


def need(ok):
    if not ok:
        raise Stop(REASON)


def identity(row):
    need(type(row) is dict)
    need(type(row.get('device')) is int and row['device'] > 0 and
         type(row.get('inode')) is int and row['inode'] > 0)
    return row['device'], row['inode']


def directory(row, uid, mode):
    identity(row)
    need(row.get('kind') == 'directory' and type(row.get('uid')) is int and
         row['uid'] == uid and row.get('mode') == mode and
         row.get('defaultAcl') is False)


def prepare(inspect):
    """Inspect is injected; importing/calling with mocks performs no host operations.

    Return data only. No report supplied here is independently authenticated.
    Never treat a returned plan as execution authorization.
    """
    obs = inspect()  # one bounded observation; no retries/fallback
    need(type(obs) is dict and type(obs.get('schema')) is int and obs['schema'] == 1)
    need(obs.get('account') == 'sde-runner' and
         type(obs.get('uid')) is int and obs['uid'] == 1001 and
         type(obs.get('euid')) is int and obs['euid'] == 1001 and
         obs.get('home') == HOME)
    need(obs.get('activationDisabled') is True and
         obs.get('remoteRunnerAbsent') is True and
         obs.get('noQueuedOrActiveJobs') is True and
         obs.get('dedicatedAccountQuiescent') is True and
         obs.get('localRegistrationAbsent') is True)
    # Explicit facts, not missing/falsey defaults, are required throughout.
    need(obs.get('scanComplete') is True and obs.get('scanStable') is True and
         type(obs.get('scanSeconds')) in (int, float) and
         0 <= obs['scanSeconds'] <= 30)
    need(obs.get('groups') == ['kvm', 'sde-runner', 'users'])
    dirs = obs.get('directories')
    need(type(dirs) is dict and set(dirs) == {'/', '/home', HOME, SOURCE, LEGACY})
    for path in ('/', '/home'):
        directory(dirs[path], 0, '0755')
    directory(dirs[HOME], 1001, '0750')
    directory(dirs[SOURCE], 1001, '0700')
    need(identity(dirs[SOURCE]) == IDENTITY)
    # The older failed session is recorded/preserved, never traversed or changed.
    legacy = dirs[LEGACY]
    identity(legacy)
    need(legacy.get('kind') == 'directory' and legacy.get('uid') == 1001 and
         legacy.get('mode') == '0700')
    need(obs.get('archiveAbsent') is True and
         obs.get('noReplaceRenameAvailable') is True and
         obs.get('sameFilesystem') is True and
         identity(dirs[HOME])[0] == IDENTITY[0])
    return {
        'kind': 'session-archive-setup-plan', 'executionAuthorized': False,
        'source': SOURCE, 'destination': ARCHIVE,
        'sourceIdentity': list(IDENTITY), 'legacyIdentity': list(identity(legacy)),
        'preserve': [LEGACY, ARCHIVE], 'recursiveChanges': False,
        'operations': [
            {'op': 'rename-no-replace', 'from': SOURCE, 'to': ARCHIVE},
            {'op': 'verify-identity', 'path': ARCHIVE, 'identity': list(IDENTITY)},
            {'op': 'mkdir-exclusive', 'path': SOURCE, 'mode': '0700'},
            {'op': 'mkdir-exclusive', 'path': WORK, 'mode': '0700'},
        ],
        'requires': ['fresh-authorization', 'live-observation', 'descriptor-relative-paths',
                     'pre-mutation-revalidation', 'no-replace-rename',
                     'parent-directory-fsync', 'bounded-durable-phase-journal',
                     'postcondition-readback'],
        'onFailure': 'stop-preserve-state-no-retry-no-rollback',
        'nativeValidated': False,
    }
