import unittest
from scripts.policy import decide, activated

def usage(reset_at, used=0, weekly=0):
 return {'rate_limit':{'primary_window':{'reset_at':reset_at,'used_percent':used,'limit_window_seconds':18000},'secondary_window':{'used_percent':weekly}}}

class PolicyTests(unittest.TestCase):
 def test_active_window_skips(self):
  self.assertEqual(decide(usage(12000,30),10000,0),'skip')
 def test_weekly_exhaustion_never_sends(self):
  self.assertEqual(decide(usage(28000,0,100),10000,0),'blocked')
 def test_unavailable_meter_never_sends(self):
  self.assertEqual(decide(None,10000,0),'unknown')
 def test_cold_window_sends(self):
  self.assertEqual(decide(usage(28000),10000,0),'send')
 def test_recent_send_prevents_duplicates(self):
  self.assertEqual(decide(usage(28000),10000,9900),'skip')
 def test_sliding_timer_is_not_verified(self):
  self.assertFalse(activated(usage(28000),usage(28020),10000,10020))
 def test_pinned_timer_is_verified(self):
  self.assertTrue(activated(usage(28000),usage(28000),10000,10020))
 def test_missing_meter_is_not_verified(self):
  self.assertFalse(activated(usage(28000),None,10000,10020))

if __name__=='__main__': unittest.main()
