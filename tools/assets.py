"""Acquire the pinned public asset snapshot; never run legacy city generators."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def safe_path(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or '\\' in value or ':' in value or any(p in ('..', '.') for p in value.split('/')):
        raise ValueError('Unsafe asset path: ' + value)
    return path


def verify(directory, manifest):
    directory = Path(directory)
    for relative, meta in manifest['files'].items():
        file = directory / safe_path(relative)
        if not file.is_file() or file.is_symlink() or directory.resolve() not in file.resolve().parents:
            raise ValueError('Missing or unsafe asset: ' + relative)
        if file.stat().st_size != meta['bytes'] or digest(file) != meta['sha256']:
            raise ValueError('Asset hash mismatch: ' + relative)
        with file.open('rb') as f:
            if f.read(42).startswith(b'version https://git-lfs.github.com/spec/'):
                raise ValueError('LFS pointer is not an asset: ' + relative)
    return len(manifest['files'])


def install_archive(archive, destination, manifest):
    destination = Path(destination)
    if destination.exists():
        raise ValueError('Destination exists; preserve it or use another --output directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.assets-', dir=destination.parent) as tmp:
        staged = Path(tmp) / 'public'
        staged.mkdir()
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            if len(names) != len(set(names)) or set(names) != set(manifest['files']):
                raise ValueError('Archive contents differ from the pinned manifest')
            for info in z.infolist():
                target = staged / safe_path(info.filename)
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Symlink in asset archive')
                if info.file_size != manifest['files'][info.filename]['bytes']:
                    raise ValueError('Archive size differs from manifest')
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as source, target.open('wb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
        verify(staged, manifest)
        os.replace(staged, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'fetch', 'verify', 'pack'])
    parser.add_argument('--plan', action='store_true', help='compatible read-only asset plan')
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'public')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'assets/runtime-manifest.json').read_text())
    lock = json.loads((ROOT / 'assets/runtime-lock.json').read_text())
    if args.command == 'plan' or args.plan:
        print(json.dumps({'source': lock, 'fileCount': len(manifest['files']), 'bytes': sum(m['bytes'] for m in manifest['files'].values()), 'installed': args.output.exists(), 'rebuildGuide': 'docs/REBUILDING.md', 'fullSourceRebuildVerified': False}, indent=2))
    elif args.command == 'verify':
        print('Verified', verify(args.output, manifest), 'runtime assets')
    elif args.command == 'pack':
        verify(args.output, manifest)
        archive = args.archive or ROOT / 'artifacts/gta-hz-runtime.zip'
        archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
            for relative in sorted(manifest['files']):
                z.write(args.output / relative, relative)
        print(json.dumps({'file': str(archive), 'sha256': digest(archive), 'bytes': archive.stat().st_size}))
    else:
        if args.output.exists():
            print('Existing assets:', verify(args.output, manifest), 'verified; unchanged')
            return
        archive = args.archive
        if archive is None:
            cache = ROOT / '.cache'; cache.mkdir(exist_ok=True)
            archive = cache / 'runtime.zip'
            if not archive.exists() or digest(archive) != lock['sha256']:
                partial = cache / 'runtime.zip.part'
                request = urllib.request.Request(lock['url'], headers={'User-Agent': 'GTA_HZ-assets/1'})
                with urllib.request.urlopen(request, timeout=60) as source, partial.open('wb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                if digest(partial) != lock['sha256']:
                    partial.unlink()
                    raise ValueError('Downloaded archive SHA256 mismatch')
                os.replace(partial, archive)
        if digest(archive) != lock['sha256']:
            raise ValueError('Archive SHA256 mismatch')
        install_archive(archive, args.output, manifest)
        print('Installed', len(manifest['files']), 'verified assets')


if __name__ == '__main__':
    main()
