class SelfUpdater:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def apply_update(self, file_path: str, content: str):
        if not file_path or not isinstance(content, str):
            raise ValueError("A file path and content are required.")

        normalized = file_path.strip()
        if normalized.startswith("/") or normalized.startswith(".."):
            raise ValueError("Only project-local files can be updated.")

        full_path = self.base_dir + "/" + normalized
        with open(full_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return {"path": normalized, "updated": True}
