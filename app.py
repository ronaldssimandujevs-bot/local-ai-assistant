from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from assistant.agent import LocalTaskOrchestrator
from assistant.file_tools import WorkspaceManager
from assistant.local_llm import LocalLLM
from assistant.memory import MemoryStore
from assistant.planner import TaskPlanner
from assistant.self_update import SelfUpdater
from assistant.web_search import WebSearch
from assistant.web_fetch import WebFetcher

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Local AI Assistant")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

workspace = WorkspaceManager(str(BASE_DIR))
llm = LocalLLM()
memory = MemoryStore(str(DATA_DIR / "memory.db"))
planner = TaskPlanner()
updater = SelfUpdater(str(BASE_DIR))
search_tool = WebSearch()
fetcher = WebFetcher()
orchestrator = LocalTaskOrchestrator(workspace, llm, search_tool, fetcher, memory, planner, updater)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None
    allow_code_changes: bool = False
    allow_shell: bool = False
    approved_self_update: bool = False
    apply_changes: bool = False
    self_update_files: list[dict] | None = None


class FeedbackRequest(BaseModel):
    session_id: str
    rating: int = Field(ge=1, le=5)
    note: str = ""


@app.get("/", response_class=HTMLResponse)
async def read_root():
    return templates.TemplateResponse("index.html", {"request": {}})


@app.get("/api/health")
async def health():
    return {"status": "ok", "workspace": str(BASE_DIR), "has_ollama": llm.is_available()}


@app.get("/api/brain")
async def brain():
    return {"preferences": memory.get_preferences(), "summary": memory.get_learning_summary(), "recent": memory.get_recent(10)}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        return orchestrator.handle(
            prompt=request.message,
            allow_code_changes=request.allow_code_changes,
            allow_shell=request.allow_shell,
            approved_self_update=request.approved_self_update,
            apply_changes=request.apply_changes,
            self_update_files=request.self_update_files,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/feedback")
async def feedback(payload: FeedbackRequest):
    memory.record_feedback(payload.session_id, payload.rating, payload.note)
    return {"status": "ok"}


@app.get("/api/history")
async def history():
    return {"history": memory.get_recent(20), "preferences": memory.get_preferences(), "summary": memory.get_learning_summary()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
