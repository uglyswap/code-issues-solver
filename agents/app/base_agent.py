import json
from typing import Dict, Any, Optional
from jinja2 import Template

from integrations.app.llm_client import BaseLLMClient


class BaseAgent:
    def __init__(self, name: str, prompt_template: str, client: BaseLLMClient, model: str, temperature: float = 0.7, max_tokens: int = 4000):
        self.name = name
        self.prompt_template = Template(prompt_template)
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def render_prompt(self, context: Dict[str, Any]) -> str:
        return self.prompt_template.render(**context)

    async def run(self, context: Dict[str, Any]) -> str:
        prompt = self.render_prompt(context)
        response = await self.client.chat_completion(
            model=self.model,
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": json.dumps(context, default=str)}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response

    async def run_json(self, context: Dict[str, Any]) -> Any:
        text = await self.run(context)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Attempt to extract JSON from markdown code blocks
            import re
            match = re.search(r"```(?:json)?\n(.*?)\n```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise
