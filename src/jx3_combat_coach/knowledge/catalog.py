"""Local reference data. Labels are not verified mechanics; exact level only."""
import json
import os
from pathlib import Path


class ReferenceCatalog:
    def __init__(self):
        path = Path(os.getenv('JX3_CATALOG_PATH', 'local-data/catalog.json'))
        self.data = json.loads(path.read_text()) if path.exists() else {'entries': {}}

    def lookup(self, kind: str, resource_id: str | None, level: int | None):
        entry = self.data['entries'].get(f'{kind}.{resource_id}_{level}')
        return dict(entry, client=self.data.get('client'), game_version=self.data.get('game_version'), version_match='unverified') if entry else None
