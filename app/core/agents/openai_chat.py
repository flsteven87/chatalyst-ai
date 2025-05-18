import openai
from typing import List, Dict
from app.config import OPENAI_API_KEY, AI_MODEL


class OpenAIChatAgent:
    """Simple chat agent using OpenAI ChatCompletion."""

    def __init__(self, model: str | None = None) -> None:
        self.api_key = OPENAI_API_KEY
        self.model = model or AI_MODEL or "gpt-3.5-turbo"
        openai.api_key = self.api_key

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Send chat messages to the OpenAI API and return the reply."""
        resp = openai.ChatCompletion.create(model=self.model, messages=messages)
        return resp["choices"][0]["message"]["content"].strip()
