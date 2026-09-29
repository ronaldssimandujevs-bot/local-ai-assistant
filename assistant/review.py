import difflib
from pathlib import Path


class ReviewManager:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()

    def preview_file_update(self, path: str, new_content: str) -> dict:
        full_path = (self.workspace_root / path).resolve()
        if self.workspace_root not in full_path.parents and full_path != self.workspace_root:
            raise ValueError(f"Access denied outside workspace: {path}")

        current = ""
        try:
            current = full_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            current = ""

        diff = list(
            difflib.unified_diff(
                current.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"{path} (current)",
                tofile=f"{path} (proposed)",
            )
        )

        return {
            "path": path,
            "status": "new" if not current else "modified",
            "preview": "".join(diff) or "No visual diff; file contents are effectively the same.",
            "old_size": len(current),
            "new_size": len(new_content),
        }

    def preview_self_update(self, file_updates: list[dict]) -> list[dict]:
        previews = []
        for item in file_updates:
            path = item.get("path")
            content = item.get("content", "")
            if not path:
                continue
            previews.append(self.preview_file_update(path, content))
        return previews
