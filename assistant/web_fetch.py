import re


class TaskPlanner:
    def plan(self, prompt: str):
        text = prompt.strip()
        lower = text.lower()
        if re.search(r"\b(remember|prefer|always)\b", lower):
            return {"category": "preference", "value": re.sub(r"^(remember|prefer|always)\s+(that\s+)?", "", text, flags=re.I).strip(" .?!")}
        if lower.startswith(("search ", "look up ", "latest ")) or "news" in lower:
            return {"category": "search", "value": re.sub(r"^(search|look up|latest)\s+", "", text, flags=re.I).strip() or text}
        url = re.search(r"https?://[^\s]+", text)
        if url and any(word in lower for word in ("open", "visit", "fetch", "read", "browse")):
            return {"category": "fetch_url", "value": url.group(0).rstrip(".,)")}
        if lower.startswith(("read file ", "open file ")):
            return {"category": "read_file", "value": re.sub(r"^(read|open) file\s+", "", text, flags=re.I).strip('"\'')}
        if lower.startswith(("write code ", "create code ", "generate code ")):
            raw = re.sub(r"^(write|create|generate) code\s+", "", text, flags=re.I)
            match = re.match(r"(?:in|to)\s+([^:]+):\s*(.+)$", raw, flags=re.S | re.I)
            return {"category": "generate_code", "path": match.group(1).strip() if match else "generated.py", "value": match.group(2).strip() if match else raw}
        if lower.startswith(("write file ", "create file ", "modify file ")):
            raw = re.sub(r"^(write|create|modify) file\s+", "", text, flags=re.I)
            if re.search(r"\s+with content\s+", raw, flags=re.I):
                path, content = re.split(r"\s+with content\s+", raw, maxsplit=1, flags=re.I)
                return {"category": "write_file", "path": path.strip('"\''), "value": content}
            return {"category": "write_file", "path": raw.strip('"\''), "value": ""}
        if "self update" in lower or "update your own code" in lower or "update yourself" in lower:
            return {"category": "self_update", "value": text}
        if lower.startswith("run ") or lower.startswith("execute "):
            return {"category": "run_shell", "value": re.sub(r"^(run|execute)\s+", "", text, flags=re.I)}
        return {"category": "chat", "value": text}
