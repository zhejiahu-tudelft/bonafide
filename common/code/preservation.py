"""Hash preservation that honours documented retirements and amendments.

A preserved file passes when its bytes still match the recorded hash, or when a change
record explains it: a retired file was replaced by a stable public URL, a derived copy
was removed because its original is retained, or a file was deliberately amended. The
record keeps the original hash, so a restored or re-downloaded copy remains verifiable.
"""
import hashlib, json, re
from pathlib import Path

# SEC's CDN appends one per-request script tag before </body>; the filed document
# is otherwise byte-identical. Content hashes are taken with that tag removed.
CDN_TAG = re.compile(rb'<script type="text/javascript"\s+src="/[A-Za-z0-9_/+\-]*"></script>')

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def content_sha256(data):
    return sha256(CDN_TAG.sub(b'', data))

def load_changes(path):
    path = Path(path)
    if not path.exists():
        return {}
    return {c['path']: c for c in json.loads(path.read_text())['changes']}

def verify(manifest, repo, changes_path, prefix=''):
    """Return problems for a {path: sha256} manifest; an empty list means preserved.

    `prefix` is prepended to manifest paths that are relative to a subdirectory,
    so every record is keyed by its repository-relative path.
    """
    repo = Path(repo); changes = load_changes(changes_path); problems = []
    for path, expected in manifest.items():
        key = prefix + path; p = repo / key; c = changes.get(key)
        if c is None:
            if not p.exists():
                problems.append(f'{key}: missing')
            elif sha256(p.read_bytes()) != expected:
                problems.append(f'{key}: changed')
            continue
        if c['original_sha256'] != expected:
            problems.append(f'{key}: change record does not match the preserved hash')
        elif c['action'] == 'amended':
            if not p.exists() or sha256(p.read_bytes()) != c['current_sha256']:
                problems.append(f'{key}: differs from its recorded amendment')
        elif c['action'] in ('retired', 'removed_derived'):
            if c['action'] == 'retired' and not c.get('url'):
                problems.append(f'{key}: retired without a source URL')
            # A restored copy is acceptable if it is the original or the same filing.
            if p.exists():
                data = p.read_bytes()
                if sha256(data) != expected and content_sha256(data) != c.get('content_sha256'):
                    problems.append(f'{key}: restored copy does not match the record')
        else:
            problems.append(f'{key}: unknown change action {c["action"]!r}')
    return problems

def accounted(path, repo, changes_path):
    """True when a referenced local file exists or is covered by a retirement record."""
    repo = Path(repo)
    c = load_changes(changes_path).get(path)
    return (repo / path).exists() or (c is not None and c['action'] in ('retired', 'removed_derived'))
