"""Explicit local import: python scripts/import_reference.py /path/to/jx3-death-review."""
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
entries = {}
sources = {}
for relative in ['data/replay-name-catalog.json', 'data/buff-reference.json']:
    path = root / relative
    data = json.loads(path.read_text())
    sources[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    if 'entries' in data:
        for key, item in data['entries'].items():
            if item.get('name'):
                entries[key] = dict(kind=item['kind'], id=item['id'], level=item['level'], name=item['name'], tags=[], source=relative, verified=False)
    else:
        for buff in data['buffs'].values():
            for level, item in buff['levels'].items():
                key = f"buff.{buff['id']}_{level}"
                entries[key] = dict(kind='buff', id=buff['id'], level=int(level), name=item.get('name'), tags=item.get('categories', []), source=relative, verified=False)
output = Path('local-data/catalog.json')
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(dict(client='std', game_version='std-2026-10-30', source_repository='https://github.com/Akatsuki-kurumi/jx3-death-review', source_hashes=sources, entries=entries), ensure_ascii=False))
print(f'Imported {len(entries)} local reference entries into {output}')
