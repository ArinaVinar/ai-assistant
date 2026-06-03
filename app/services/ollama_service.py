import json
import requests

from app.config import settings


class OllamaService:
    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        response = requests.post(url, json=payload, timeout=180)
        response.raise_for_status()

        data = response.json()
        return data.get("response", "").strip()

    def generate_json(self, prompt: str, temperature: float = 0.0) -> dict:
        raw = self.generate(prompt, temperature=temperature)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")

            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start:end + 1])
                except json.JSONDecodeError:
                    pass

        return {
            "parse_error": True,
            "raw": raw,
        }


ollama_service = OllamaService()