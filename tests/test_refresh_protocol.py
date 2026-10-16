import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from auth_refresh import refresh_auth

class ProtocolTests(unittest.TestCase):
 def exercise(self, response):
  with tempfile.TemporaryDirectory() as root:
   cli=Path(root)/'codex'
   cli.write_text('#!/usr/bin/env python3\nimport json,sys\nfor line in sys.stdin:\n m=json.loads(line)\n if m.get("id")==1: print(json.dumps({"id":1,"result":{}}),flush=True)\n if m.get("id")==2: print('+repr(response)+',flush=True)\n')
   cli.chmod(0o700)
   with patch.dict(os.environ,{'PATH':root+os.pathsep+os.environ['PATH']}): return refresh_auth()
 def test_successful_handshake(self):
  self.assertTrue(self.exercise('{"id":2,"result":{"account":{"type":"chatgpt"}}}'))
 def test_server_error(self):
  self.assertFalse(self.exercise('{"id":2,"error":{"code":-1,"message":"not logged in"}}'))
 def test_no_account_is_not_refresh_success(self):
  self.assertFalse(self.exercise('{"id":2,"result":{"account":null}}'))
