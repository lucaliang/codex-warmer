import contextlib,io,sys,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import warm

class RefreshTests(unittest.TestCase):
 def test_401_refreshes_persists_then_retries(self):
  with patch.object(warm,'fetch_meter',side_effect=[urllib.error.HTTPError('hidden',401,'hidden',{},None),{'ok':True}]), patch.object(warm,'refresh_auth',return_value=True) as refresh, patch.object(warm,'digest',return_value=b'old'), patch.object(warm,'persist',return_value=True) as persist, contextlib.redirect_stdout(io.StringIO()):
   self.assertEqual(warm.meter(),{'ok':True});refresh.assert_called_once();persist.assert_called_once_with(b'old')
 def test_failed_persistence_does_not_continue(self):
  with patch.object(warm,'fetch_meter',side_effect=urllib.error.HTTPError('hidden',401,'hidden',{},None)), patch.object(warm,'refresh_auth',return_value=True), patch.object(warm,'digest',return_value=b'old'), patch.object(warm,'persist',return_value=False),contextlib.redirect_stdout(io.StringIO()):
   self.assertIsNone(warm.meter())
