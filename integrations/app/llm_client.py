import asyncio
import httpx
from typing import List, Dict, Any, Optional


# Codes HTTP retryables (transitoires). 429 = rate limit, 5xx = erreurs serveur.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BASE_BACKOFF = 1.0


class BaseLLMClient:
    def __init__(self, api_key: str, base_url: str):
        # NOTE: la cle API est passee en header du client long-vie. Ne jamais la logger.
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
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_exc: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.post("/chat/completions", json=payload)
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                # Ne retry que 429 et 5xx; les autres 4xx sont definitifs.
                if status in _RETRYABLE_STATUS and attempt < _MAX_RETRIES - 1:
                    last_exc = exc
                    await asyncio.sleep(_BASE_BACKOFF * (2 ** attempt))
                    continue
                raise
            except httpx.TransportError as exc:
                # Erreurs reseau transitoires (timeout, connexion, etc.).
                if attempt < _MAX_RETRIES - 1:
                    last_exc = exc
                    await asyncio.sleep(_BASE_BACKOFF * (2 ** attempt))
                    continue
                raise
        else:
            # Boucle epuisee sans break (securite; normalement inatteignable).
            if last_exc is not None:
                raise last_exc
            raise RuntimeError("LLM request failed after retries")

        try:
            data = response.json()
        except ValueError as exc:
            snippet = response.text[:500]
            raise RuntimeError(
                f"LLM response is not valid JSON: {snippet}"
            ) from exc

        # Parsing defensif: la structure attendue peut etre absente si l'API
        # renvoie une erreur sous forme de JSON ou une reponse malformee.
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected LLM response shape: {str(data)[:500]}")

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError(
                f"LLM response missing 'choices': {str(data)[:500]}"
            )

        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise RuntimeError(
                f"LLM response missing message content: {str(data)[:500]}"
            )

        return content

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
