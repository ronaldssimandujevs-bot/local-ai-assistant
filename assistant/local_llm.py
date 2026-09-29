import os
import requests


class LocalLLM:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    def is_available(self) -> bool:
        try:
            result = requests.get(f"{self.base_url}/api/tags", timeout=4)
            return result.status_code == 200
        except requests.RequestException:
            return False

    def generate_reply(self, prompt: str, memory: list | None = None) -> str:
        if self.is_available():
            try:
                payload = {
                    "model": "llama3.2:latest",
                    "prompt": self._build_prompt(prompt, memory),
                    "stream": False,
                    "options": {"temperature": 0.6},
                }
                response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                return data.get("response", self._fallback_prompt(prompt)).strip()
            except Exception:
                return self._fallback_prompt(prompt)
        return self._fallback_prompt(prompt)

    def _build_prompt(self, prompt: str, memory: list | None) -> str:
        context = ""
        if memory:
            context = "\n".join(
                [f"User: {item.get('user_input')}\nAssistant: {item.get('assistant_output')}" for item in memory[-4:]]
            )
        return f"You are a helpful local AI assistant. Follow the user's instructions carefully.\nCurrent memory:\n{context}\nUser: {prompt}\nAssistant:"

    def _fallback_prompt(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "search" in prompt_lower or "latest" in prompt_lower:
            return "I can perform a web search when connected, and I can also keep a local memory of your previous requests. For a specific topic, ask me to search and I will fetch the latest available information."
        if "code" in prompt_lower or "file" in prompt_lower or "modify" in prompt_lower:
            return "I can read project files, create or modify content, and update the assistant itself when you explicitly authorize the change. I will explain the proposed change before executing it."
        if "voice" in prompt_lower:
            return "Voice input is available through the browser microphone. I can respond to spoken requests and help you control the local assistant with commands like 'open project', 'search for X', or 'create a file'."
        return "I am running locally and can help with research, file work, and software tasks. Tell me what you want to do, and I will guide the next step."
