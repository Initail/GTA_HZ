"""Read a bounded tail of the current monitor; stale/missing data fails closed."""
import json,math
from datetime import datetime, timezone
from pathlib import Path

def probe_guard_status(file, now=None):
    now=now or datetime.now(timezone.utc)
    try:
        with Path(file).open('rb') as stream:
            stream.seek(0,2);size=stream.tell();assert size<=1024*1024
            offset=max(0,size-65536);stream.seek(offset);tail=stream.read(65536)
        if offset:
            tail=tail.split(b'\n',1)[1]
        complete=tail.split(b'\n')[:-1]
        row=json.loads(next(line for line in reversed(complete) if line.strip()))
        age=(now-datetime.fromisoformat(row['atUTC'])).total_seconds()
        assert isinstance(row['sample'],int) and row['sample']>=0
        assert isinstance(row['alarms'],list) and all(isinstance(s,str) for s in row['alarms'])
        assert isinstance(row['rssGrowthKiB'],(int,float)) and math.isfinite(row['rssGrowthKiB'])
        reason=None
        if row['alarms']:reason='resource-alarm'
        elif row['memoryPressure']!='1':reason='memory-pressure'
        elif row['rssGrowthKiB']>512*1024:reason='rss-limit'
        elif not 0<=age<=9:reason='stale-monitor'
        return {'ready':reason is None,'stop':reason is not None,'reason':reason,'sample':row['sample']}
    except (OSError,ValueError,TypeError,KeyError,AssertionError,StopIteration,IndexError):
        return {'ready':False,'stop':True,'reason':'monitor-unavailable','sample':None}
