import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import warm

class RunnerTests(unittest.TestCase):
 def setUp(self):
  self.tmp = tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.auth = Path(self.tmp.name)/'auth.json'
  self.auth.write_text('fake-credential')
  self.state = Path(self.tmp.name)/'state'/'last'
  for name,value in [('AUTH',self.auth),('STATE',self.state)]:
   p=patch.object(warm,name,value); p.start(); self.addCleanup(p.stop)
  p=patch.dict(os.environ,{'WARM_MODEL':'test-model','GITHUB_REPOSITORY':'test/repo'});p.start();self.addCleanup(p.stop)

 def execute(self, decision='send', verification=True, persistence=True, timeout=False, verify_request=False):
  calls=[]
  def cli(*args,**kwargs):
   calls.append((args,kwargs))
   if timeout: raise subprocess.TimeoutExpired('codex',120)
   return subprocess.CompletedProcess(args[0],0)
  with patch.object(warm,'meter',return_value={}), patch.object(warm,'decide',return_value=decision), patch.object(warm,'activated',return_value=verification), patch.object(warm,'persist',return_value=persistence) as save, patch.object(warm.time,'sleep'), patch.object(warm.subprocess,'run',side_effect=cli), contextlib.redirect_stdout(io.StringIO()) as output:
   code=warm.run(verify_request=verify_request)
  self.assertNotIn('fake-credential',output.getvalue())
  return code,calls,save

 def test_active_window_never_invokes_cli(self):
  code,calls,_=self.execute(decision='skip');self.assertEqual(code,0);self.assertEqual(calls,[])
 def test_unknown_meter_fails_without_cli(self):
  code,calls,_=self.execute(decision='unknown');self.assertEqual(code,1);self.assertEqual(calls,[])
 def test_unverified_send_fails_but_records_timestamp(self):
  code,calls,save=self.execute(verification=False);self.assertEqual(code,1);self.assertEqual(len(calls),1);self.assertTrue(self.state.exists());save.assert_called_once()
 def test_persistence_failure_fails_verified_request(self):
  code,_,_=self.execute(persistence=False);self.assertEqual(code,1)
 def test_timeout_still_persists_and_never_retries(self):
  code,calls,save=self.execute(timeout=True);self.assertEqual(code,1);self.assertEqual(len(calls),1);save.assert_called_once()
 def test_changed_credentials_go_over_stdin_only(self):
  with patch.object(warm.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as call, contextlib.redirect_stdout(io.StringIO()):
   self.assertTrue(warm.persist(b'changed'))
  args,kwargs=call.call_args
  self.assertNotIn('fake-credential',' '.join(args[0]));self.assertEqual(kwargs['input'],b'fake-credential')


 def test_diagnostic_request_still_obeys_weekly_block(self):
  code,calls,_=self.execute(decision='blocked',verify_request=True)
  self.assertEqual(code,0); self.assertEqual(calls,[])
 def test_diagnostic_request_can_test_active_window(self):
  code,calls,_=self.execute(decision='skip',verify_request=True)
  self.assertEqual(code,0); self.assertEqual(len(calls),1)

if __name__=='__main__': unittest.main()
