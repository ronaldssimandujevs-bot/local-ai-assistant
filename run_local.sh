import subprocess
from pathlib import Path


class SafeExecutor:
    def __init__(self, working_dir: str):
        self.working_dir = Path(working_dir)

    def run(self, command: str, timeout: int = 120):
        if not command or not command.strip():
            raise ValueError("A command is required.")

        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(self.working_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if completed.returncode not in (0,):
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Command failed.")

        return {
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "returncode": completed.returncode,
        }
