import re


class TaskPlanner:
    def plan(self, prompt: str):
        text = prompt.strip()
        lowered = text.lower()

        if re.search(r"(?:remember|prefer|like|want|always).*?(?:i\s+)?(?:prefer|like|want|am\s+happy\s+with)", lowered):
            match = re.search(r"(?:prefer|like|want|remember|always)\s+(?:that\s+)?(?:i\s+)?(?:prefer|like|want|am\s+happy\s+with)?\s*(.+)$", lowered)
            value = (match.group(1) if match else text).strip(" .?!")
            return {"category": "preference", "value": value}

        if "search" in lowered or "look up" in lowered or "latest" in lowered or "news" in lowered:
            for prefix in ("search ", "look up ", "latest "):
                if lowered.startswith(prefix):
                    value = text[len(prefix):].strip()
                    return {"category": "search", "value": value}
            return {"category": "search", "value": text}

        if "read file" in lowered or "open file" in lowered:
            value = text.replace("read file", "").replace("open file", "").strip().strip('"\'')
            return {"category": "read_file", "value": value or "README.md"}

        if "read " in lowered and "." in lowered:
            value = text.replace("read ", "", 1).strip().strip('"\'')
            return {"category": "read_file", "value": value}

        if "write file" in lowered or "create file" in lowered or "modify file" in lowered:
            raw = text
            if "write file" in lowered:
                raw = raw.split("write file", 1)[1].strip()
            elif "create file" in lowered:
                raw = raw.split("create file", 1)[1].strip()
            else:
                raw = raw.split("modify file", 1)[1].strip()

            if " with content " in lowered:
                path, content = raw.split(" with content ", 1)
                return {"category": "write_file", "path": path.strip().strip('"\''), "value": content.strip()}

            return {"category": "write_file", "path": raw.strip().strip('"\''), "value": ""}

        if "self update" in lowered or "update your own code" in lowered or "update yourself" in lowered:
            return {"category": "self_update", "value": text}

        if lowered.startswith("run ") or "execute" in lowered or "shell" in lowered:
            command = text.replace("run ", "", 1).strip() if lowered.startswith("run ") else text.strip()
            return {"category": "run_shell", "value": command}

        return {"category": "chat", "value": text}
