import os
import re
from pathlib import Path


class WorkspaceManager:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir).resolve()

    def _safe_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path).expanduser()
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.base_dir / candidate).resolve()

        if self.base_dir not in resolved.parents and resolved != self.base_dir:
            raise ValueError(f"Access denied outside workspace: {raw_path}")
        return resolved

    def list_directory(self, path: str = "."):
        resolved = self._safe_path(path)
        return [p.name for p in resolved.iterdir()]

    def read_file(self, path: str) -> str:
        resolved = self._safe_path(path)
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        return resolved.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> str:
        resolved = self._safe_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return str(resolved)

    def exists(self, path: str) -> bool:
        try:
            return self._safe_path(path).exists()
        except ValueError:
            return False
