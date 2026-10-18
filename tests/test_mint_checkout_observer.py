"""Mocked/static only; never run a listener or native observer on this host."""
import ast
import io
import json
from pathlib import Path
from types import SimpleNamespace as S
import unittest
from unittest.mock import Mock, patch
import yaml
import observe_mint_checkout as o

ROOT=Path(__file__).resolve().parents[1]
HOME=Path('/home/sde-runner')
SESSION=HOME/'mint-prep-runner-private-session'
CHECKOUT=SESSION/'_work-private'/'Tactics-Strategy-Dev-Environments'/'Tactics-Strategy-Dev-Environments'
SNAPSHOTS={name:('synthetic source '+name).encode() for name in o.SOURCES}


def env():
    return dict(GITHUB_ACTIONS='true',GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_REPOSITORY=o.REPO,
        GITHUB_REF='refs/heads/main',GITHUB_WORKFLOW_REF=o.WORKFLOW,GITHUB_JOB='observe',
        GITHUB_SHA='a'*40,CHECKOUT_APPROVED_SHA='a'*40,CHECKOUT_WORKFLOW_SHA='a'*40,
        CHECKOUT_ENABLED='true',CHECKOUT_ACCESS_READY='verified',CHECKOUT_BUNDLE_SHA256=o.bundle_digest(SNAPSHOTS),
        GITHUB_RUN_ATTEMPT='1',GITHUB_RUN_ID='123',GITHUB_WORKSPACE=str(CHECKOUT))


def st(mode=0o100600,uid=1001,size=3,ino=1):
    return S(st_mode=mode,st_uid=uid,st_size=size,st_nlink=1,st_dev=1,st_ino=ino,st_mtime_ns=1,st_ctime_ns=1)


class Observer(unittest.TestCase):
    def setUp(self):
        for obj,name,value in [(o.os,'getuid',1001),(o.os,'geteuid',1001),(o.os,'getgid',1001),
            (o.os,'getgroups',[]),(o.pwd,'getpwuid',S(pw_name='sde-runner',pw_dir=str(HOME))),
            (o.grp,'getgrgid',S(gr_name='sde-runner')),(o.platform,'system','Linux'),(o.platform,'machine','x86_64')]:
            item=patch.object(obj,name,return_value=value);item.start();self.addCleanup(item.stop)
        item=patch.object(o,'__file__',str(CHECKOUT/'tests/observe_mint_checkout.py'));item.start();self.addCleanup(item.stop)
        self.snapshot=Mock(side_effect=lambda root,name,*rest:SNAPSHOTS[name])
        self.mask=Mock(return_value='0077')
        self.reader=Mock(return_value=b'RELEASE=22.3\n')
        self.evidence={}

    def execute(self,changes=None):
        return o.run(dict(env(),**(changes or {})),self.evidence,snapshot=self.snapshot,
                     mask=self.mask,reader=self.reader,clock=lambda:0)

    def test_all_missing_gates_stop_before_observation(self):
        for key in env():
            if key=='GITHUB_WORKSPACE':continue
            with self.subTest(key=key),self.assertRaises(o.Stop):self.execute({key:''})
        self.mask.assert_not_called();self.snapshot.assert_not_called();self.reader.assert_not_called()

    def test_wrong_context_ref_attempt_location_and_account_stop(self):
        for key,value in [('GITHUB_EVENT_NAME','pull_request'),('GITHUB_EVENT_NAME','push'),
            ('GITHUB_EVENT_NAME','workflow_call'),('GITHUB_REPOSITORY','fork/repo'),('GITHUB_REF','other'),
            ('CHECKOUT_WORKFLOW_SHA','b'*40),('CHECKOUT_APPROVED_SHA','b'*40),('GITHUB_RUN_ATTEMPT','2'),
            ('GITHUB_WORKSPACE','/other'),('GITHUB_JOB','prepare')]:
            with self.subTest(key=key),self.assertRaises(o.Stop):self.execute({key:value})
        with patch.object(o.os,'geteuid',return_value=0),self.assertRaisesRegex(o.Stop,'ACCOUNT'):self.execute()
        with patch.object(o.grp,'getgrgid',return_value=S(gr_name='sudo')),self.assertRaisesRegex(o.Stop,'GROUPS'):self.execute()
        self.snapshot.assert_not_called();self.mask.assert_not_called()

    def test_healthy_synthetic_observation_still_claims_no_media_or_cleanup(self):
        self.execute()
        raw,code=o.export(self.evidence,True,'CHECKOUT_VALIDATED')
        report=json.loads(raw)
        self.assertEqual(code,0);self.assertTrue(report['pass'])
        self.assertEqual(report['mediaAuthentication'],'NotRun')
        self.assertEqual(report['cleanupCorrectness'],'NotValidated')
        self.assertFalse(report['guestExecuted']);self.assertFalse(report['productionReady'])
        self.assertEqual(self.snapshot.call_count,len(o.SOURCES))
        self.assertEqual(self.reader.call_args.args[:3],(Path('/etc/linuxmint/info'),0,8192))

    def test_wrong_umask_host_release_and_bundle_stop(self):
        self.mask.return_value='0002'
        with self.assertRaisesRegex(o.Stop,'UMASK'):self.execute()
        self.snapshot.assert_not_called();self.reader.assert_not_called()
        self.mask.return_value='0077';self.reader.return_value=b'RELEASE=22.2\n'
        with self.assertRaisesRegex(o.Stop,'MINT_RELEASE'):self.execute()
        self.reader.return_value=b'RELEASE=22.3\n'
        self.snapshot.side_effect=lambda root,name,*rest:SNAPSHOTS[name]+b'changed'
        with self.assertRaisesRegex(o.Stop,'BUNDLE_BINDING'):self.execute()

    def test_snapshot_retains_offending_metadata_and_rejects_old_modes(self):
        path=CHECKOUT/o.SOURCES[0]
        paths={x:st(0o40755,0) for x in path.parents}
        paths[HOME]=st(0o40750)
        for x in path.parents:
            if x==SESSION or SESSION in x.parents:paths[x]=st(0o40700)
        paths[path]=st()
        for bad_path,mode,reason in [(CHECKOUT,0o40775,'SOURCE_OWNER'),
                                     (path,0o100664,'SOURCE_FILE'),(path,0o120777,'SOURCE_FILE')]:
            data=dict(paths);data[bad_path]=st(mode)
            evidence={'paths':{},'files':[]}
            with patch.object(o.Path,'lstat',autospec=True,side_effect=lambda p:data[p]), \
                 patch.object(o.os,'listxattr',return_value=[]),patch.object(o,'read_regular') as read, \
                 self.assertRaisesRegex(o.Stop,reason):
                o.source_snapshot(CHECKOUT,o.SOURCES[0],1001,SESSION,evidence,lambda:0,10)
            read.assert_not_called()
            self.assertTrue(evidence['paths'])

    def test_private_snapshot_records_hash_and_rejects_default_acl(self):
        path=CHECKOUT/o.SOURCES[0]
        paths={x:st(0o40755,0) for x in path.parents}
        paths[HOME]=st(0o40750)
        for x in path.parents:
            if x==SESSION or SESSION in x.parents:paths[x]=st(0o40700)
        paths[path]=st()
        for attributes in ([],['system.posix_acl_default']):
            evidence={'paths':{},'files':[]}
            with patch.object(o.Path,'lstat',autospec=True,side_effect=lambda p:paths[p]), \
                 patch.object(o.os,'listxattr',return_value=attributes), \
                 patch.object(o,'read_regular',return_value=b'abc') as read:
                if attributes:
                    with self.assertRaisesRegex(o.Stop,'PRIVATE_DIRECTORY'):
                        o.source_snapshot(CHECKOUT,o.SOURCES[0],1001,SESSION,evidence,lambda:0,10)
                    read.assert_not_called()
                else:
                    self.assertEqual(o.source_snapshot(CHECKOUT,o.SOURCES[0],1001,SESSION,evidence,lambda:0,10),b'abc')
                    self.assertEqual(evidence['files'][0]['sha256'],o.hashlib.sha256(b'abc').hexdigest())

    def test_acl_evidence_distinguishes_unchecked_and_failed_query(self):
        path=CHECKOUT/o.SOURCES[0]
        paths={x:st(0o40755,0) for x in path.parents}
        paths[HOME]=st(0o40750)
        for x in path.parents:
            if x==SESSION or SESSION in x.parents:paths[x]=st(0o40700)
        paths[path]=st()
        evidence={'paths':{},'files':[]}
        with patch.object(o.Path,'lstat',autospec=True,side_effect=lambda p:paths[p]), \
             patch.object(o.os,'listxattr',side_effect=OSError('private detail')) as acl, \
             patch.object(o,'read_regular') as read,self.assertRaises(OSError):
            o.source_snapshot(CHECKOUT,o.SOURCES[0],1001,SESSION,evidence,lambda:0,10)
        acl.assert_called_once_with(SESSION,follow_symlinks=False)
        read.assert_not_called()
        self.assertIsNone(evidence['paths'][str(HOME)]['defaultAcl'])
        self.assertIsNone(evidence['paths'][str(SESSION)]['defaultAcl'])
        self.assertEqual(evidence['paths'][str(SESSION)]['mode'],'0700')

    def test_ancestry_change_and_inventory_bound_stop_before_source_read(self):
        path=CHECKOUT/o.SOURCES[0]
        evidence={'paths':{'/':{'changed':True}},'files':[]}
        with patch.object(o.Path,'lstat',return_value=st(0o40755,0)), \
             patch.object(o,'read_regular') as read,self.assertRaisesRegex(o.Stop,'ANCESTRY_CHANGED'):
            o.source_snapshot(CHECKOUT,o.SOURCES[0],1001,SESSION,evidence,lambda:0,10)
        read.assert_not_called()
        evidence={'paths':{str(i):{} for i in range(32)},'files':[]}
        with patch.object(o.Path,'lstat',return_value=st(0o40755,0)), \
             patch.object(o,'read_regular') as read,self.assertRaisesRegex(o.Stop,'EVIDENCE_BOUND'):
            o.source_snapshot(CHECKOUT,o.SOURCES[0],1001,SESSION,evidence,lambda:0,10)
        self.assertEqual(len(evidence['paths']),32);read.assert_not_called()

    def test_deadline_during_read_closes_once_without_retry(self):
        with patch.object(o.os,'open',return_value=8),patch.object(o.os,'fstat',return_value=st()), \
             patch.object(o.os,'read') as read,patch.object(o.os,'close') as close, \
             self.assertRaisesRegex(o.Stop,'DEADLINE'):
            o.read_regular(Path('/fixed'),1001,10,Mock(side_effect=[0,10]),10)
        read.assert_not_called();close.assert_called_once_with(8)

    def test_deadline_stops_before_snapshot_metadata(self):
        with patch.object(o.Path,'lstat') as metadata,self.assertRaisesRegex(o.Stop,'DEADLINE'):
            o.source_snapshot(CHECKOUT,o.SOURCES[0],1001,SESSION,{'paths':{},'files':[]},lambda:10,10)
        metadata.assert_not_called()

    def test_bundle_covers_observer_and_existing_preparation_sources(self):
        self.assertEqual(len(o.SOURCES),6)
        for name in o.SOURCES:
            changed=dict(SNAPSHOTS);changed[name]+=b'x'
            self.assertNotEqual(o.bundle_digest(changed),o.bundle_digest(SNAPSHOTS))

    def test_failure_main_sanitizes_and_bounds_output(self):
        for error,reason in [(o.Stop('SOURCE_OWNER'),'SOURCE_OWNER'),(RuntimeError('SECRET_TOKEN'),'OBSERVATION_STOPPED')]:
            output=io.StringIO()
            with patch.object(o,'run',side_effect=error),patch.object(o.sys,'argv',['observer']),patch('sys.stdout',output):
                self.assertEqual(o.main(),1)
            report=json.loads(output.getvalue());self.assertEqual(report['reason'],reason)
            self.assertFalse(report['pass']);self.assertNotIn('SECRET_TOKEN',output.getvalue())
        raw,code=o.export({'oversized':'x'*o.EXPORT_LIMIT},True,'CHECKOUT_VALIDATED')
        self.assertEqual(code,1);self.assertEqual(json.loads(raw)['reason'],'EXPORT_BOUND')

    def test_read_regular_bounds_identity_nonblocking_and_cleanup(self):
        info=st()
        with patch.object(o.os,'open',return_value=8) as opened,patch.object(o.os,'fstat',return_value=info), \
             patch.object(o.os,'read',side_effect=[b'abc',b'']),patch.object(o.os,'close') as close:
            self.assertEqual(o.read_regular(Path('/fixed'),1001,10,lambda:0,10),b'abc')
        self.assertTrue(opened.call_args.args[1]&o.os.O_NONBLOCK)
        self.assertFalse(opened.call_args.args[1]&o.os.O_CREAT)
        close.assert_called_once_with(8)
        info.st_size=100
        with patch.object(o.os,'open',return_value=8),patch.object(o.os,'fstat',return_value=info), \
             patch.object(o.os,'read') as read,patch.object(o.os,'close'),self.assertRaises(o.Stop):
            o.read_regular(Path('/fixed'),1001,10,lambda:0,10)
        read.assert_not_called()

    def test_short_changing_source_and_uncertain_close_stop(self):
        for data,after in [(b'ab',st()),(b'abc',st(ino=2))]:
            with patch.object(o.os,'open',return_value=8),patch.object(o.os,'fstat',side_effect=[st(),after]), \
                 patch.object(o.os,'read',side_effect=[data,b'']),patch.object(o.os,'close') as close, \
                 self.assertRaisesRegex(o.Stop,'SOURCE_CHANGED'):
                o.read_regular(Path('/fixed'),1001,10,lambda:0,10)
            close.assert_called_once_with(8)
        with patch.object(o.os,'open',return_value=8),patch.object(o.os,'fstat',side_effect=OSError('synthetic')), \
             patch.object(o.os,'close',side_effect=OSError('synthetic close')) as close, \
             self.assertRaisesRegex(o.Stop,'DESCRIPTOR_CLEANUP_UNCERTAIN'):
            o.read_regular(Path('/fixed'),1001,10,lambda:0,10)
        close.assert_called_once_with(8)

    def test_cli_arguments_refused_before_run(self):
        with patch.object(o,'run') as run,patch.object(o.sys,'argv',['observer','--path=/other']), \
             patch('sys.stdout',io.StringIO()):self.assertEqual(o.main(),1)
        run.assert_not_called()

    def test_umask_is_read_from_fixed_proc_path_without_mutation(self):
        for raw,reason in [(b'Name:\tpython\nUmask:\t0077\n',None),
                           (b'Umask:\t0077\nUmask:\t0002\n','UMASK_MISSING'),
                           (b'Umask:\n0077\n','UMASK_MISSING'),(b'x'*16385,'STATUS_BOUND')]:
            with patch.object(o.os,'open',return_value=8) as opened,patch.object(o.os,'read',return_value=raw), \
                 patch.object(o.os,'close') as close,patch.object(o.os,'umask',side_effect=AssertionError('mutation')):
                if reason:
                    with self.assertRaisesRegex(o.Stop,reason):o.observed_umask(lambda:0,10)
                else:self.assertEqual(o.observed_umask(lambda:0,10),'0077')
            self.assertEqual(opened.call_args.args[0],'/proc/self/status');close.assert_called_once_with(8)


class Workflow(unittest.TestCase):
    def setUp(self):
        self.w=yaml.load((ROOT/'.github/workflows/mint-checkout-validation.yml').read_text(),Loader=yaml.BaseLoader)
        self.job=self.w['jobs']['observe']

    def test_disabled_gate_and_automatic_events_never_schedule_observer(self):
        good={'github.event_name':'workflow_dispatch','github.repository':o.REPO,'github.ref':'refs/heads/main',
              'github.workflow_ref':o.WORKFLOW,'github.sha':'a'*40,'github.workflow_sha':'a'*40,'github.run_attempt':1,
              'vars.MINT_CHECKOUT_ENABLED':'true','vars.MINT_CHECKOUT_ACCESS_READY':'verified',
              'vars.MINT_CHECKOUT_APPROVED_SHA':'a'*40,'vars.MINT_CHECKOUT_BUNDLE_SHA256':'b'*64}
        def allowed(values):
            code=self.job['if']
            for key in sorted(values,key=len,reverse=True):code=code.replace(key,repr(values[key]))
            return eval(code.replace('&&',' and '),{'__builtins__':{}},{})
        self.assertTrue(allowed(good))
        for key in good:
            value=2 if key=='github.run_attempt' else ''
            self.assertFalse(allowed(dict(good,**{key:value})),key)
        for event in ('pull_request','push','workflow_call','workflow_run'):
            self.assertFalse(allowed(dict(good,**{'github.event_name':event})))
        self.assertNotIn('MINT_PREP_',self.job['if'])

    def test_fixed_job_uses_identical_checkout_and_only_observer_command(self):
        self.assertEqual(self.w['on'],{'workflow_dispatch':''})
        self.assertEqual(self.w['permissions'],{'contents':'read'})
        self.assertEqual(self.w['concurrency'],{'group':'spare-mint-host','cancel-in-progress':'false'})
        self.assertEqual(set(self.w['jobs']),{'observe'})
        self.assertEqual(self.job['runs-on'],{'group':'org/sde-mint-isolated','labels':'sde-mint-prep'})
        self.assertEqual(self.job['environment'],'mint-host-access');self.assertEqual(self.job['timeout-minutes'],'10')
        prep=yaml.load((ROOT/'.github/workflows/mint-media-console-prep.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(self.job['steps'][0],prep['jobs']['prepare']['steps'][0])
        self.assertEqual(len(self.job['steps']),2)
        self.assertEqual(self.job['steps'][1]['run'],'/usr/bin/python3 -I -B tests/observe_mint_checkout.py')
        self.assertEqual(set(self.job['steps'][1]['env']),{'CHECKOUT_ENABLED','CHECKOUT_ACCESS_READY',
                         'CHECKOUT_APPROVED_SHA','CHECKOUT_WORKFLOW_SHA','CHECKOUT_BUNDLE_SHA256'})

    def test_observer_has_no_repository_import_or_native_execution_ports(self):
        tree=ast.parse((ROOT/'tests/observe_mint_checkout.py').read_text())
        allowed={'hashlib','json','os','pathlib','platform','pwd','grp','re','stat','sys','time'}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):self.assertTrue(all(x.name in allowed for x in node.names))
            if isinstance(node,ast.ImportFrom):self.assertIn(node.module,allowed)
            if isinstance(node,ast.Call):
                if isinstance(node.func,ast.Name):self.assertNotIn(node.func.id,{'eval','exec','__import__','open'})
                if isinstance(node.func,ast.Attribute):
                    if node.func.attr=='system':
                        self.assertIsInstance(node.func.value,ast.Name)
                        self.assertEqual(node.func.value.id,'platform')
                    self.assertNotIn(node.func.attr,{'umask','chmod','chown','fchmod','mkdir','makedirs','unlink',
                        'remove','rmdir','rename','replace','write','Popen','execv','execve','ioctl','socket'})


if __name__=='__main__':unittest.main()
