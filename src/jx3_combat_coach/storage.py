"""Small SQLite repository; open one connection per operation."""
import sqlite3
from pathlib import Path
from uuid import uuid4
from jx3_combat_coach.models import Analysis


class AnalysisRepository:
    def __init__(self, path: str):
        self.path = path

    def initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def save(self, analysis: Analysis) -> str:
        analysis_id = uuid4().hex
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO analyses VALUES (?, ?)", (analysis_id, analysis.model_dump_json()))
        return analysis_id

    def get(self, analysis_id: str) -> Analysis | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT payload FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return Analysis.model_validate_json(row[0]) if row else None
