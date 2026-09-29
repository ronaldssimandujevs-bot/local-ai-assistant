import subprocess

from assistant.review import ReviewManager


class LocalTaskOrchestrator:
    def __init__(self, workspace, llm, search_tool, fetcher, memory, planner, updater):
        self.workspace = workspace
        self.llm = llm
        self.search_tool = search_tool
        self.fetcher = fetcher
        self.memory = memory
        self.planner = planner
        self.updater = updater
        self.review = ReviewManager(self.workspace.base_dir)

    def _result(self, prompt, text, category, actions=None, preferences=None):
        self.memory.record_interaction(prompt, text, category)
        return {"response": text, "actions": actions or [], "memory": self.memory.get_recent(5), "preferences": preferences or self.memory.get_preferences()}

    def handle(self, prompt, allow_code_changes=False, allow_shell=False, approved_self_update=False, apply_changes=False, self_update_files=None):
        prompt = (prompt or "").strip()
        if not prompt:
            raise ValueError("A message is required.")
        preferences = self.memory.get_preferences()
        intent = self.planner.plan(prompt)
        category = intent["category"]

        if category == "preference":
            self.memory.remember_preference("user_preference", intent["value"])
            return self._result(prompt, f"Noted. I’ll remember that you prefer: {intent['value']}", category, preferences=preferences)

        if category == "search":
            results = self.search_tool.search(intent["value"])
            text = "Current results for '{}':\n{}".format(intent["value"], "\n".join(f"- {x['title']}: {x['url']}" for x in results[:5]))
            return self._result(prompt, text, category, preferences=preferences)

        if category == "fetch_url":
            try:
                page = self.fetcher.fetch(intent["value"])
                text = f"Fetched {page['url']}\n\n{page['text'][:8000]}"
                return self._result(prompt, text, category, [{"type": "fetch_url", "url": page["url"]}], preferences)
            except Exception as exc:
                return self._result(prompt, f"I could not access that URL: {exc}", category, preferences=preferences)

        if category == "read_file":
            try:
                content = self.workspace.read_file(intent["value"])
                return self._result(prompt, f"Contents of {intent['value']}:\n```\n{content[:8000]}\n```", category, [{"type": "read_file", "path": intent["value"]}], preferences)
            except Exception as exc:
                return self._result(prompt, f"I couldn't read that file: {exc}", category, preferences=preferences)

        if category in {"generate_code", "write_file"}:
            if category == "generate_code":
                path = intent.get("path") or "generated.py"
                content = self.llm.generate_code(intent["value"], path)
            else:
                path, content = intent["path"], intent["value"]
            preview = self.review.preview_file_update(path, content)
            action = {"type": "code_preview", "path": path, "preview": preview}
            if not allow_code_changes or not apply_changes:
                text = f"Proposed code for {path}. Review it, then enable code changes and apply changes to write it:\n\n```diff\n{preview['preview']}\n```\n\nGenerated content:\n```\n{content[:12000]}\n```"
                return self._result(prompt, text, "code_preview", [action], preferences)
            try:
                self.workspace.write_file(path, content)
                return self._result(prompt, f"Approved code change applied to {path}.", "code_write", [{"type": "write_file", "path": path}], preferences)
            except Exception as exc:
                return self._result(prompt, f"I couldn't write that code: {exc}", "code_write_failed", preferences=preferences)

        if category == "self_update":
            if not approved_self_update:
                return self._result(prompt, "Self-update requires explicit authorization and a reviewed file payload.", category, [{"type": "approval", "message": "Allow self-update"}], preferences)
            files = self_update_files or []
            if not files:
                return self._result(prompt, "No self-update files were supplied.", category, preferences=preferences)
            previews = self.review.preview_self_update(files)
            if not apply_changes:
                return self._result(prompt, "Self-update preview; enable Apply changes only after reviewing it:\n\n" + "\n".join(f"{x['path']}\n```diff\n{x['preview']}\n```" for x in previews), "self_update_preview", [{"type": "self_update_preview", "files": previews}], preferences)
            for item in files:
                self.updater.apply_update(item["path"], item.get("content", ""))
            return self._result(prompt, "Authorized self-update applied: " + ", ".join(x["path"] for x in files), "self_update", [{"type": "self_update", "files": files}], preferences)

        if category == "run_shell":
            if not allow_shell:
                return self._result(prompt, "Shell execution requires explicit permission.", category, [{"type": "approval", "message": "Allow shell execution"}], preferences)
            try:
                completed = subprocess.run(intent["value"], shell=True, cwd=str(self.workspace.base_dir), capture_output=True, text=True, timeout=120)
                output = completed.stdout.strip() or completed.stderr.strip() or "Command finished without output."
                return self._result(prompt, f"Command exit code {completed.returncode}:\n{output[:4000]}", category, [{"type": "shell", "command": intent["value"]}], preferences)
            except Exception as exc:
                return self._result(prompt, f"Command failed: {exc}", category, preferences=preferences)

        return self._result(prompt, self.llm.generate_reply(prompt, self.memory.get_recent(8), preferences), "chat", preferences=preferences)
