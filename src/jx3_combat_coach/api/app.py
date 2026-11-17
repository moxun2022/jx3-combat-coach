import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
from pydantic import Field
from jx3_combat_coach.models import Analysis, Model
from jx3_combat_coach.service import analyze
from jx3_combat_coach.storage import AnalysisRepository
from jx3_combat_coach.replay import replay, evidence_report
from jx3_combat_coach.agent.report import generate_report, ReportUnavailable


class AnalyzeRequest(Model):
    text: str = Field(max_length=1_000_000)


class AnalyzeResponse(Model):
    analysis_id: str
    analysis: Analysis


def create_app(database_path: str | None = None) -> FastAPI:
    repository = AnalysisRepository(database_path or os.getenv("JX3_DATABASE_PATH", "combat-coach.sqlite3"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repository.initialize()
        yield

    app = FastAPI(title="JX3 Combat Coach", version="0.1.0", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index():
        return (Path(__file__).parent / "index.html").read_text(encoding="utf-8")

    @app.post("/api/v1/analyses/file", response_model=AnalyzeResponse, status_code=201)
    async def analyze_file(request: Request, encoding: str = "utf-8-sig"):
        if encoding not in {"utf-8-sig", "utf-8", "gbk", "gb18030"}:
            raise HTTPException(422, "Unsupported encoding")
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 10_000_000:
                raise HTTPException(413, "File exceeds 10 MB")
        analysis = analyze(bytes(data), encoding)
        return AnalyzeResponse(analysis_id=repository.save(analysis), analysis=analysis)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/analyses", response_model=AnalyzeResponse, status_code=201)
    def create_analysis(request: AnalyzeRequest):
        analysis = analyze(request.text.encode("utf-8"))
        return AnalyzeResponse(analysis_id=repository.save(analysis), analysis=analysis)

    @app.get("/api/v1/analyses/{analysis_id}", response_model=Analysis)
    def get_analysis(analysis_id: str):
        analysis = repository.get(analysis_id)
        if analysis is None:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return analysis

    def require_analysis(analysis_id: str):
        analysis = repository.get(analysis_id)
        if analysis is None:
            raise HTTPException(404, "Analysis not found")
        return analysis

    @app.get("/api/v1/analyses/{analysis_id}/replay")
    def get_replay(analysis_id: str):
        return replay(require_analysis(analysis_id))

    @app.get("/api/v1/analyses/{analysis_id}/report")
    def get_report(analysis_id: str):
        return evidence_report(replay(require_analysis(analysis_id)))

    @app.post("/api/v1/analyses/{analysis_id}/report/ai")
    def ai_report(analysis_id: str):
        try:
            return generate_report(replay(require_analysis(analysis_id)))
        except ReportUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

    return app


app = create_app()
