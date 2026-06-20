import httpx
from typing import List, Dict, Any, Optional


class BaseLLMClient:
    def __init__(self, api_key: str, base_url: str):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def close(self):
        await self.client.aclose()


class OpenRouterClient(BaseLLMClient):
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://openrouter.ai/api/v1")
        self.client.headers["HTTP-Referer"] = "https://code-issues-solver.local"
        self.client.headers["X-Title"] = "Code Issues Solver"


class AlibabaCloudClient(BaseLLMClient):
    def __init__(self, api_key: str, base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        super().__init__(api_key, base_url)
