"""Prepare complete near-pack tasks from pinned source manifests, without
opening GLBs. This is a coverage/task plan, not a playable release or cost pass.
Run once through run_hangzhou_bounded.py in a fresh candidate directory.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'terrain': ('stream-mesh-v1', 'c9c8411696782cb657f83a016ba0716c3b992359a14a877aaf9789e25dd75a91'),
    'roads': ('stream-mesh-v1', 'a26341aa20a324381914c1a2c2bbfbb9fc0f0f95214bdb11dba60424790359e5'),
    'buildings': ('stream-mesh-v2', '85745d9064000cb387bee3c65b74952076ca839d7cbf8587f189e1105448ef6d'),
}


def prepare(output: Path):
    assert not output.exists(), 'Fresh candidate directory required'
    groups = defaultdict(list)
    sources = {}
    source_ids = set()
    totals = {'bytes': 0, 'logicalBytes': 0, 'triangles': 0, 'tiles': 0}
    for role, (version, expected_hash) in SOURCES.items():
        file = ROOT / 'artifacts/cities/hangzhou' / version / role / 'manifest.json'
        assert file.stat().st_size <= 256 * 1024
        raw = file.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected_hash, 'Source manifest changed'
        doc = json.loads(raw)
        assert doc['role'] == role and doc['tileSizeGame'] == 640
        sources[role] = {'manifest': str(file.relative_to(ROOT)), 'sha256': expected_hash, 'bytes': len(raw)}
        for tile in doc['tiles']:
            assert tile['id'] not in source_ids
            source_ids.add(tile['id'])
            prefix, coordinate = tile['id'].split(':')
            assert prefix == role
            x, z = map(int, coordinate.split(','))
            # Adjacent 2x2 source cells. Negative coordinates use floor division,
            # matching the city grid rather than truncating towards zero.
            groups[(x // 2, z // 2)].append({
                'role': role, 'quality': 'near', 'id': tile['id'],
                'manifest': sources[role]['manifest'], 'manifestSha256': expected_hash,
                'sha256': tile['sha256'], 'bytes': tile['bytes'],
                'logicalBytes': tile['logicalBytes'], 'triangles': tile['triangles'],
            })
            for key in ('bytes', 'logicalBytes', 'triangles'):
                totals[key] += tile[key]
            totals['tiles'] += 1
    tasks = []
    for (x, z), members in sorted(groups.items()):
        assert len(members) <= 12
        # Sum of original files bounds the merged BIN but not an arbitrary new
        # header. Keep margin; the physical writer independently checks exact
        # header/file sizes and refuses oversized packs rather than splitting
        # a supposedly complete output behind the index's back.
        queue, size, logical, part = [], 0, 0, 0
        for member in members:
            assert member['bytes'] <= 7 * 1024 * 1024 and member['logicalBytes'] <= 30 * 1024 * 1024
            if queue and (size + member['bytes'] > 7 * 1024 * 1024 or logical + member['logicalBytes'] > 30 * 1024 * 1024):
                tasks.append({'schemaVersion': 1, 'id': f'near-{x}-{z}-{part}', 'members': queue})
                queue, size, logical, part = [], 0, 0, part + 1
            queue.append(member)
            size += member['bytes']
            logical += member['logicalBytes']
        if queue:
            tasks.append({'schemaVersion': 1, 'id': f'near-{x}-{z}-{part}', 'members': queue})
    assert len(source_ids) == sum(len(task['members']) for task in tasks)
    output.mkdir(parents=True)
    entries = []
    for task in tasks:
        task['scope'] = 'exact near geometry; not a full-view resource or playable acceptance'
        file = output / 'tasks' / task['id'] / 'task.json'
        file.parent.mkdir(parents=True)
        data = (json.dumps(task, ensure_ascii=False, indent=2) + '\n').encode()
        file.write_bytes(data)
        entries.append({'id': task['id'], 'task': str(file.relative_to(output)), 'sha256': hashlib.sha256(data).hexdigest(), 'members': len(task['members'])})
    plan = {'schemaVersion': 1, 'kind': 'base-pack-task-plan', 'sources': sources,
            'tasks': entries, 'sourceTotals': totals, 'nearMembers': len(source_ids),
            'physicalPacksPlanned': len(tasks), 'geometryExecuted': False,
            'fullViewCostPassed': False, 'browserValidated': False, 'runtimeInstalled': False}
    (output / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'nearMembers': len(source_ids), 'tasks': len(tasks), 'executedGLBs': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    prepare(parser.parse_args().output.resolve())
