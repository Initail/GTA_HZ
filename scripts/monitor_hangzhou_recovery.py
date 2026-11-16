"""Read-only, short resource sampling. Never terminates a shared browser/app."""
import json
import re
import subprocess
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

output = Path(sys.argv[1])
if output.exists():
    raise SystemExit('Choose a new evidence filename.')
baseline = None
hot = {}
with output.open('w') as log:
    for index in range(18):
        rows = []
        for line in subprocess.check_output(['ps', '-axo', 'pid,ppid,%cpu,rss,comm'], text=True).splitlines()[1:]:
            parts = line.strip().split(None, 4)
            if len(parts) == 5 and '/Applications/ChatGPT.app/' in parts[4]:
                pid, ppid, cpu, rss, comm = parts
                rows.append({'pid': int(pid), 'ppid': int(ppid), 'cpuPercent': float(cpu), 'rssKiB': int(rss), 'name': Path(comm).name})
        rss = sum(r['rssKiB'] for r in rows)
        if baseline is None:
            baseline = rss
        pressure = subprocess.check_output(['sysctl', '-n', 'kern.memorystatus_vm_pressure_level'], text=True).strip()
        gpu = subprocess.run(['ioreg', '-r', '-c', 'AGXAccelerator', '-l'], capture_output=True, text=True, timeout=5)
        counts = dict(re.findall(r'"(Device Utilization %|Renderer Utilization %|Tiler Utilization %)"\s*=\s*(\d+)', gpu.stdout))
        for row in rows:
            hot[row['pid']] = hot.get(row['pid'], 0) + 1 if row['cpuPercent'] > 100 else 0
        alarms = []
        if pressure != '1':
            alarms.append('system-memory-pressure-not-normal')
        if rss - baseline > 512 * 1024:
            alarms.append('app-family-rss-growth-over-512MiB')
        if any(hot[row['pid']] >= 2 for row in rows):
            alarms.append('app-process-over-100pct-cpu-in-two-samples')
        row = {'atUTC': datetime.now(timezone.utc).isoformat(), 'sample': index, 'memoryPressure': pressure,
               'appFamilyRssKiB': rss, 'rssGrowthKiB': rss - baseline, 'processes': rows,
               'gpuPercent': {k: int(v) for k, v in counts.items()} if counts else None, 'alarms': alarms,
               'scope': 'host/app-wide counters, not game attribution; RSS sum can include shared pages'}
        log.write(json.dumps(row) + '\n')
        log.flush()
        if alarms:
            print(json.dumps(row), flush=True)
            break
        if index < 17:
            time.sleep(5)
print('Resource sampling ended; no processes were killed.', flush=True)
