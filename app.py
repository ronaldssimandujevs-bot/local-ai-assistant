from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import re
import subprocess

from assistant.file_tools import WorkspaceManager
from assistant.local_llm import LocalLLM
from assistant.memory import MemoryStore
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
updater = SelfUpdater(base_dir=str(BASE_DIR))


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


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="A message is required.")

    prompt = request.message.strip()
    lower = prompt.lower()
    actions = []
    preferences = memory.get_preferences()

    if "remember" in lower or "prefer" in lower:
        preference_match = re.search(r"(?:remember|prefer|always|like)\s+(?:that\s+)?(?:i\s+)?(?:prefer|like|want|am\s+happy\s+with)\s+(.+)$", prompt, re.I)
        if preference_match:
            pref = preference_match.group(1).strip().strip(".?!")
            key = "user_preference"
            memory.remember_preference(key, pref)
            text = f"Noted. I’ll remember that you prefer: {pref}"
            memory.record_interaction(prompt, text, "preference")
            return {"response": text, "actions": actions, "memory": memory.get_recent(5), "preferences": preferences}

    if "search" in lower or "look up" in lower or "latest" in lower:
        query = prompt
        if query.lower().startswith("search "):
            query = query[7:]
        elif query.lower().startswith("look up "):
            query = query[8:]
        elif query.lower().startswith("latest "):
            query = query[7:]
        results = search_tool.search(query)
        text = f"Here are current web results for '{query}':\n"
        for item in results[:5]:
            text += f"- {item['title']}: {item['url']}\n"
        text += "\nI can use those to support your next step."
        memory.record_interaction(prompt, text, "web_search")
        return {"response": text, "actions": actions, "memory": memory.get_recent(5), "preferences": preferences}

    if "read file" in lower or "open file" in lower or ("read " in lower and "." in lower):
        candidate = prompt.replace("read file", "").replace("open file", "").strip().strip('"\'')
        if not candidate:
            text = "I need a file path to read. Example: read file README.md"
        else:
            try:
                content = workspace.read_file(candidate)
                text = f"Contents of {candidate}:\n```\n{content[:4000]}\n```"
                actions.append({"type": "read_file", "path": candidate})
            except Exception as exc:
                text = f"I couldn't read that file: {exc}"
        memory.record_interaction(prompt, text, "file_read")
        return {"response": text, "actions": actions, "memory": memory.get_recent(5), "preferences": preferences}

    if "write file" in lower or "create file" in lower or "modify file" in lower:
        if not request.allow_code_changes:
            text = "I can write or modify files only after you explicitly allow code changes."
            memory.record_interaction(prompt, text, "permission_needed")
            return {"response": text, "actions": [{"type": "approval", "message": "Allow code changes"}], "memory": memory.get_recent(5), "preferences": preferences}

        raw = prompt
        if "write file" in lower:
            raw = raw.split("write file", 1)[1].strip()
        elif "create file" in lower:
            raw = raw.split("create file", 1)[1].strip()
        elif "modify file" in lower:
            raw = raw.split("modify file", 1)[1].strip()

        parts = raw.split(" with content ", 1)
        if len(parts) != 2:
            text = "Use the format: write file path/to/file.txt with content ..."
            memory.record_interaction(prompt, text, "file_write_failed")
            return {"response": text, "actions": [], "memory": memory.get_recent(5), "preferences": preferences}

        path = parts[0].strip().strip('"\'')
        content = parts[1].strip()
        try:
            workspace.write_file(path, content)
            text = f"File written successfully to {path}."
            actions.append({"type": "write_file", "path": path})
        except Exception as exc:
            text = f"I couldn't write that file: {exc}"
        memory.record_interaction(prompt, text, "file_write")
        return {"response": text, "actions": actions, "memory": memory.get_recent(5), "preferences": preferences}

    if "self update" in lower or "update your own code" in lower or "update yourself" in lower:
        if not request.approved_self_update:
            text = "I can update my own code only after an explicit authorization. Please confirm that you want me to modify my own source files."
            memory.record_interaction(prompt, text, "self_update_pending")
            return {"response": text, "actions": [{"type": "approval", "message": "Allow self-update"}], "memory": memory.get_recent(5), "preferences": preferences}

        files = request.self_update_files or []
        if not files:
            text = "No files were supplied for a self-update. Example payload: {\"self_update_files\":[{\"path\":\"README.md\",\"content\":\"text\"}]}."
            memory.record_interaction(prompt, text, "self_update_missing")
            return {"response": text, "actions": [], "memory": memory.get_recent(5), "preferences": preferences}

        updated = []
        for item in files:
            path = item.get("path")
            content = item.get("content", "")
            if not path:
                continue
            try:
                updater.apply_update(path, content)
                updated.append(path)
            except Exception as exc:
                text = f"Update failed for {path}: {exc}"
                memory.record_interaction(prompt, text, "self_update_failed")
                return {"response": text, "actions": [], "memory": memory.get_recent(5), "preferences": preferences}

        text = "Self-update completed successfully for: " + ", ".join(updated)
        memory.record_interaction(prompt, text, "self_update")
        return {"response": text, "actions": [{"type": "self_update", "files": updated}], "memory": memory.get_recent(5), "preferences": preferences}

    if lower.startswith("run ") or "execute" in lower or "shell" in lower:
        if not request.allow_shell:
            text = "I can run commands only after you explicitly allow shell execution."
            memory.record_interaction(prompt, text, "shell_permission_needed")
            return {"response": text, "actions": [{"type": "approval", "message": "Allow shell execution"}], "memory": memory.get_recent(5), "preferences": preferences}

        command = prompt.replace("run ", "", 1).strip() if lower.startswith("run ") else prompt.strip()
        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = completed.stdout.strip() or completed.stderr.strip() or "Command finished without output."
            text = f"Command executed successfully:\n{command}\n\nOutput:\n{output[:4000]}"
            actions.append({"type": "shell", "command": command})
        except Exception as exc:
            text = f"Command failed: {exc}"
        memory.record_interaction(prompt, text, "shell_execution")
        return {"response": text, "actions": actions, "memory": memory.get_recent(5), "preferences": preferences}

    response = llm.generate_reply(prompt, memory.get_recent(8), preferences)
    memory.record_interaction(prompt, response, "chat")
    return {"response": response, "actions": actions, "memory": memory.get_recent(5), "preferences": preferences}


@app.post("/api/feedback")
async def feedback(payload: FeedbackRequest):
    memory.record_feedback(payload.session_id, payload.rating, payload.note)
    return {"status": "ok"}


@app.get("/api/history")
async def history():
    return {"history": memory.get_recent(20), "preferences": memory.get_preferences()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
