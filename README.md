# Local AI Assistant

A local desktop-style AI assistant that runs on your computer, supports voice input, file editing, web search, and self-updates after explicit authorization.

## Features

- Local server using Python and FastAPI
- Simple browser-based UI served on your computer
- Voice input through the Web Speech API
- Local LLM support through Ollama if available
- Internet search through DuckDuckGo
- File read/write tools with a safe workspace boundary
- Self-learning memory via SQLite database
- Explicit approval gates before code changes or self-updates

## Run locally

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the app:
   ```bash
   python app.py
   ```

4. Open the app in your browser:
   ```text
   http://localhost:8000
   ```

## Optional: use Ollama locally

If you want the assistant to use a real local model, install Ollama and pull a model.

```bash
ollama serve
ollama pull llama3.2:latest
```

The assistant will automatically use Ollama if it is available.

## Example commands

- "Search for the latest React release notes"
- "Read file README.md"
- "Write file notes.txt with content Hello world"
- "Update your own code after explicit authorization"

## Safety

This project is intentionally restrictive:

- Files are only editable within the local project directory.
- Shell commands are not executed without explicit permission.
- Self-updates require a dedicated approval flag and file payload.

## Project structure

```text
app.py
assistant/
  file_tools.py
  local_llm.py
  memory.py
  self_update.py
  web_search.py
templates/
  index.html
static/
  app.js
  styles.css
data/
  memory.db
requirements.txt
```
