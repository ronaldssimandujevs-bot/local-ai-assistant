import subprocess
from typing import Any


class LocalTaskOrchestrator:
    def __init__(self, workspace, llm, search_tool, memory, planner, updater):
        self.workspace = workspace
        self.llm = llm
        self.search_tool = search_tool
        self.memory = memory
        self.planner = planner
        self.updater = updater

    def handle(self, prompt: str, allow_code_changes: bool = False, allow_shell: bool = False, approved_self_update: bool = False, self_update_files: list | None = None):
        text_prompt = (prompt or "").strip()
        if not text_prompt:
            raise ValueError("A message is required.")

        lower = text_prompt.lower()
        actions = []
        preferences = self.memory.get_preferences()
        intent = self.planner.plan(text_prompt)

        if intent["category"] == "preference":
            value = intent["value"]
            self.memory.remember_preference("user_preference", value)
            result = f"Noted. I’ll remember that you prefer: {value}"
            self.memory.record_interaction(text_prompt, result, "preference")
            return {"response": result, "actions": actions, "memory": self.memory.get_recent(5), "preferences": preferences}

        if intent["category"] == "search":
            query = intent["value"]
            results = self.search_tool.search(query)
            result = f"Current results for '{query}':\n"
            for item in results[:5]:
                result += f"- {item['title']}: {item['url']}\n"
            result += "\nI can use these results to support the next step."
            self.memory.record_interaction(text_prompt, result, "web_search")
            return {"response": result, "actions": actions, "memory": self.memory.get_recent(5), "preferences": preferences}

        if intent["category"] == "read_file":
            candidate = intent["value"]
            try:
                content = self.workspace.read_file(candidate)
                result = f"Contents of {candidate}:\n```\n{content[:4000]}\n```"
                actions.append({"type": "read_file", "path": candidate})
            except Exception as exc:
                result = f"I couldn't read that file: {exc}"
            self.memory.record_interaction(text_prompt, result, "file_read")
            return {"response": result, "actions": actions, "memory": self.memory.get_recent(5), "preferences": preferences}

        if intent["category"] == "write_file":
            if not allow_code_changes:
                result = "I can write or modify files only after you explicitly allow code changes."
                self.memory.record_interaction(text_prompt, result, "permission_needed")
                return {"response": result, "actions": [{"type": "approval", "message": "Allow code changes"}], "memory": self.memory.get_recent(5), "preferences": preferences}

            path = intent["path"]
            content = intent["value"]
            try:
                self.workspace.write_file(path, content)
                result = f"File written successfully to {path}."
                actions.append({"type": "write_file", "path": path})
            except Exception as exc:
                result = f"I couldn't write that file: {exc}"
            self.memory.record_interaction(text_prompt, result, "file_write")
            return {"response": result, "actions": actions, "memory": self.memory.get_recent(5), "preferences": preferences}

        if intent["category"] == "self_update":
            if not approved_self_update:
                result = "I can update my own code only after an explicit authorization. Please confirm you want me to modify my own source files."
                self.memory.record_interaction(text_prompt, result, "self_update_pending")
                return {"response": result, "actions": [{"type": "approval", "message": "Allow self-update"}], "memory": self.memory.get_recent(5), "preferences": preferences}

            files = self_update_files or []
            if not files:
                result = "No files were supplied for a self-update."
                self.memory.record_interaction(text_prompt, result, "self_update_missing")
                return {"response": result, "actions": [], "memory": self.memory.get_recent(5), "preferences": preferences}

            updated = []
            for item in files:
                path = item.get("path")
                content = item.get("content", "")
                if not path:
                    continue
                try:
                    self.updater.apply_update(path, content)
                    updated.append(path)
                except Exception as exc:
                    result = f"Update failed for {path}: {exc}"
                    self.memory.record_interaction(text_prompt, result, "self_update_failed")
                    return {"response": result, "actions": [], "memory": self.memory.get_recent(5), "preferences": preferences}

            result = "Self-update completed successfully for: " + ", ".join(updated)
            self.memory.record_interaction(text_prompt, result, "self_update")
            return {"response": result, "actions": [{"type": "self_update", "files": updated}], "memory": self.memory.get_recent(5), "preferences": preferences}

        if intent["category"] == "run_shell":
            if not allow_shell:
                result = "I can run commands only after you explicitly allow shell execution."
                self.memory.record_interaction(text_prompt, result, "shell_permission_needed")
                return {"response": result, "actions": [{"type": "approval", "message": "Allow shell execution"}], "memory": self.memory.get_recent(5), "preferences": preferences}

            command = intent["value"]
            try:
                completed = subprocess.run(command, shell=True, cwd=str(self.workspace.base_dir), capture_output=True, text=True, timeout=120)
                output = completed.stdout.strip() or completed.stderr.strip() or "Command finished without output."
                result = f"Command executed successfully:\n{command}\n\nOutput:\n{output[:4000]}"
                actions.append({"type": "shell", "command": command})
            except Exception as exc:
                result = f"Command failed: {exc}"
            self.memory.record_interaction(text_prompt, result, "shell_execution")
            return {"response": result, "actions": actions, "memory": self.memory.get_recent(5), "preferences": preferences}

        result = self.llm.generate_reply(text_prompt, self.memory.get_recent(8), preferences)
        self.memory.record_interaction(text_prompt, result, "chat")
        return {"response": result, "actions": actions, "memory": self.memory.get_recent(5), "preferences": preferences}
