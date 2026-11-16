import json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from hangzhou_probe_guard import probe_guard_status
class GuardTests(unittest.TestCase):
 def test_resource_alarm_staleness_and_partial_write(self):
  now=datetime.now(timezone.utc);row={'atUTC':now.isoformat(),'sample':2,'memoryPressure':'1','rssGrowthKiB':0,'alarms':[]}
  with tempfile.TemporaryDirectory() as d:
   file=Path(d)/'monitor.jsonl'
   self.assertFalse(probe_guard_status(file,now)['ready'])
   def check(value):file.write_text(json.dumps(value)+'\n');return probe_guard_status(file,now)
   self.assertTrue(check(row)['ready']);self.assertEqual(check(dict(row,alarms=['limit']))['reason'],'resource-alarm')
   self.assertEqual(check(dict(row,rssGrowthKiB=512*1024+1))['reason'],'rss-limit')
   self.assertEqual(check(dict(row,memoryPressure='2'))['reason'],'memory-pressure')
   self.assertEqual(check(dict(row,atUTC=(now-timedelta(seconds=10)).isoformat()))['reason'],'stale-monitor')
   self.assertEqual(check(dict(row,atUTC=(now+timedelta(seconds=1)).isoformat()))['reason'],'stale-monitor')
   file.write_text(json.dumps(row)+'\n'+json.dumps(dict(row,sample=3))[:20]);self.assertTrue(probe_guard_status(file,now)['ready'])
   file.write_text('invalid\n');self.assertFalse(probe_guard_status(file,now)['ready'])
if __name__=='__main__':unittest.main()
