"""T1 contract/permission prototype, not a production journal consumer.

No package commands or real coordination paths. Root-only fixtures run in CI;
the ordinary suite tests the strict proposed payload without changing privileges.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import uuid

MAX_INTENT_BYTES = 4096


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate acknowledgment field')
        result[key] = value
    return result


def parse_intent(payload):
    if len(payload) > MAX_INTENT_BYTES:
        raise ValueError('Oversized acknowledgment')
    value = json.loads(payload.decode('utf-8'), object_pairs_hook=unique_fields)
    if not isinstance(value, dict) or set(value) != {'schema', 'incidentId'}:
        raise ValueError('Invalid acknowledgment fields')
    if type(value['schema']) is not int or value['schema'] != 1:
        raise ValueError('Invalid acknowledgment schema')
    incident_id = value['incidentId']
    if not isinstance(incident_id, str) or str(uuid.UUID(incident_id)) != incident_id:
        raise ValueError('Invalid incident identity')
    return incident_id


def matches_binding(payload, binding, journal):
    """Shape/matching experiment only; production must also validate all handles."""
    try:
        return (parse_intent(payload) == binding['incidentId']
                and hashlib.sha256(journal).hexdigest() == binding['journalSha256'])
    except (ValueError, UnicodeError, KeyError, TypeError):
        return False


class IntentContract(unittest.TestCase):
    def setUp(self):
        self.incident_id = '9fe3858b-58da-4b96-b47d-ec2f1b867353'
        self.intent = json.dumps({'schema': 1, 'incidentId': self.incident_id}).encode()
        self.journal = b'{"schema":1,"token":"fixture-private-token","kind":"system"}'
        self.binding = {'incidentId': self.incident_id,
                        'journalSha256': hashlib.sha256(self.journal).hexdigest()}

    def test_valid_intent_is_only_an_incident_identity(self):
        self.assertEqual(parse_intent(self.intent), self.incident_id)
        self.assertTrue(matches_binding(self.intent, self.binding, self.journal))

    def test_nonmatching_incident_is_not_acknowledged(self):
        changed = dict(self.binding, incidentId=str(uuid.uuid4()))
        self.assertFalse(matches_binding(self.intent, changed, self.journal))

    def test_same_id_does_not_acknowledge_replaced_evidence(self):
        self.assertFalse(matches_binding(self.intent, self.binding, b'new journal'))

    def test_empty_partial_oversized_or_invalid_encoding_is_not_acknowledgment(self):
        for value in (b'', b'{', b'\xff', b' ' * (MAX_INTENT_BYTES + 1)):
            with self.subTest(value_length=len(value)):
                self.assertFalse(matches_binding(value, self.binding, self.journal))

    def test_extra_fields_cannot_supply_paths_commands_or_tokens(self):
        for key in ('path', 'command', 'token', 'skip', 'operation'):
            with self.subTest(key=key):
                value = {'schema': 1, 'incidentId': self.incident_id, key: 'untrusted'}
                self.assertFalse(matches_binding(json.dumps(value).encode(), self.binding, self.journal))

    def test_schema_is_an_integer_one_not_a_truthy_value(self):
        for schema in (True, False, 0, 2, '1', 1.0, None):
            with self.subTest(schema=schema):
                value = {'schema': schema, 'incidentId': self.incident_id}
                self.assertFalse(matches_binding(json.dumps(value).encode(), self.binding, self.journal))

    def test_rejects_duplicate_fields(self):
        value = ('{"schema":1,"incidentId":"' + self.incident_id
                 + '","incidentId":"' + self.incident_id + '"}').encode()
        self.assertFalse(matches_binding(value, self.binding, self.journal))

    def test_requires_canonical_identity(self):
        for identity in (None, 1, '', '../transaction.json', self.incident_id.upper(),
                         self.incident_id.replace('-', '')):
            with self.subTest(identity=identity):
                value = {'schema': 1, 'incidentId': identity}
                self.assertFalse(matches_binding(json.dumps(value).encode(), self.binding, self.journal))

    def test_rejects_nonobject_and_missing_fields(self):
        for value in ([], None, True, {}, {'schema': 1}):
            with self.subTest(value=value):
                self.assertFalse(matches_binding(json.dumps(value).encode(), self.binding, self.journal))


@unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0
                     and os.environ.get('GITHUB_ACTIONS') == 'true',
                     'Native permission proof requires disposable Linux root CI')
class LinuxAcknowledgmentPermissions(unittest.TestCase):
    def test_student_submits_intent_without_access_to_private_evidence(self):
        # A new, explicit fixture path, never the production coordination root.
        with tempfile.TemporaryDirectory(prefix='sde-recovery-contract-', dir='/var/lib') as fixture:
            root = Path(fixture)
            root.chmod(0o755)
            journal = b'{"schema":1,"token":"private-fixture-token","kind":"system"}'
            incident_id = str(uuid.uuid4())
            private = root / 'transaction.json'
            private.write_bytes(journal)
            private.chmod(0o600)
            binding_path = root / 'recovery-binding.json'
            binding = {'incidentId': incident_id,
                       'journalSha256': hashlib.sha256(journal).hexdigest()}
            binding_path.write_text(json.dumps(binding))
            binding_path.chmod(0o600)
            public = root / 'recovery-incident.json'
            public.write_text(json.dumps({'schema': 1, 'incidentId': incident_id}))
            public.chmod(0o644)
            intent = root / 'recovery-acknowledgment.json'
            intent.touch(mode=0o600)
            intent.chmod(0o666)
            original_metadata = (private.stat().st_ino, private.stat().st_mode)
            # Keep the child self-contained: it need not read a private checkout.
            student = r'''
import json, os, sys
from pathlib import Path
p = Path(sys.argv[1])
assert os.geteuid() == 65534
snapshot = json.loads((p / 'recovery-incident.json').read_text())
assert set(snapshot) == {'schema', 'incidentId'}
slot = p / 'recovery-acknowledgment.json'
slot.write_text(json.dumps(snapshot))
for action in (
    lambda: (p / 'transaction.json').read_bytes(),
    lambda: (p / 'recovery-binding.json').read_bytes(),
    lambda: (p / 'transaction.json').write_text('unsafe'),
    lambda: (p / 'transaction.json').unlink(),
    lambda: (p / 'recovery-incident.json').write_text('unsafe'),
    lambda: (p / 'new-state').write_text('unsafe'),
    lambda: slot.unlink(),
    lambda: slot.chmod(0o777),
):
    try:
        action()
    except PermissionError:
        continue
    raise AssertionError('Student accessed protected state or replaced the slot')
print('SDE_RECOVERY_LINUX_STANDARD_USER_INTENT_OK')
'''

            def drop_privileges():
                os.setgroups([])
                os.setgid(65534)
                os.setuid(65534)

            process = subprocess.run([sys.executable, '-c', student, str(root)],
                                     preexec_fn=drop_privileges, capture_output=True,
                                     text=True, timeout=15, check=False)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIn('SDE_RECOVERY_LINUX_STANDARD_USER_INTENT_OK', process.stdout)
            self.assertEqual(private.read_bytes(), journal)
            self.assertEqual((private.stat().st_ino, private.stat().st_mode), original_metadata)
            self.assertEqual(stat.S_IMODE(intent.stat().st_mode), 0o666)
            self.assertEqual(intent.stat().st_uid, 0)
            self.assertTrue(matches_binding(intent.read_bytes(), binding, private.read_bytes()))
            # A second independent consumer can see the same decision (scheduler).
            consumer = subprocess.run([sys.executable, '-c',
                                      'import json,sys;from pathlib import Path;'
                                      'p=Path(sys.argv[1]);'
                                      'assert json.loads(p.read_text())["incidentId"]==sys.argv[2]',
                                      str(intent), incident_id], check=False, timeout=15)
            self.assertEqual(consumer.returncode, 0)
            # The old intent must not match a new generation, even after restart.
            self.assertFalse(matches_binding(intent.read_bytes(),
                                             dict(binding, incidentId=str(uuid.uuid4())), journal))


if __name__ == '__main__':
    if os.environ.get('SDE_REQUIRE_RECOVERY_FEASIBILITY') == '1' and not (
            sys.platform == 'linux' and os.geteuid() == 0
            and os.environ.get('GITHUB_ACTIONS') == 'true'):
        raise RuntimeError('Required native recovery permission proof cannot be skipped')
    unittest.main()
