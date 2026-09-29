from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path

from assistant.file_tools import WorkspaceManager
from assistant.local_llm import LocalLLM
from assistant.memory import MemoryStore
from assistant.planner import TaskPlanner
from assistant.agent import LocalTaskOrchestrator
from assistant.web_search import WebSearch
from assistant.self_update import SelfUpdater

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Local AI Assistant")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

workspace = WorkspaceManager(base_dir=str(BASE_DIR))
llm = LocalLLM()
search_tool = WebSearch()
memory = MemoryStore(str(DATA_DIR / "memory.db"))
planner = TaskPlanner()
updater = SelfUpdater(base_dir=str(BASE_DIR))
orchestrator = LocalTaskOrchestrator(workspace, llm, search_tool, memory, planner, updater)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    allow_code_changes: bool = False
    allow_shell: bool = False
    approved_self_update: bool = False
    self_update_files: list[dict] | None = None


class FeedbackRequest(BaseModel):
    session_id: str
    rating: int
    note: str = ""


@app.get("/", response_class=HTMLResponse)
async def read_root():
    return templates.TemplateResponse("index.html", {"request": {}})


@app.get("/api/health")
async def health():
    return {"status": "ok", "workspace": str(BASE_DIR), "has_ollama": llm.is_available()}


@app.get("/api/brain")
async def brain():
    return {
        "preferences": memory.get_preferences(),
        "summary": memory.get_learning_summary(),
        "recent": memory.get_recent(10),
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    response = orchestrator.handle(
        prompt=request.message,
        allow_code_changes=request.allow_code_changes,
        allow_shell=request.allow_shell,
        approved_self_update=request.approved_self_update,
        self_update_files=request.self_update_files,
    )
    return response


@app.post("/api/feedback")
async def feedback(payload: FeedbackRequest):
    memory.record_feedback(payload.session_id, payload.rating, payload.note)
    return {"status": "ok"}


@app.get("/api/history")
async def history():
    return {"history": memory.get_recent(20), "preferences": memory.get_preferences(), "summary": memory.get_learning_summary()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
