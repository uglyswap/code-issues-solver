import asyncio
import base64
import time
import urllib.parse
import httpx
from typing import Optional, List, Dict, Any, Callable, Awaitable


# Codes retryables: 403/429 (rate limit GitHub) et 5xx (erreurs serveur).
_RETRYABLE_STATUS = {500, 502, 503, 504}
_RATE_LIMIT_STATUS = {403, 429}
_MAX_RETRIES = 3
_BASE_BACKOFF = 1.0
_MAX_RATE_LIMIT_WAIT = 60.0


class GitHubClient:
    def __init__(self, token: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    @staticmethod
    def _rate_limit_wait(response: httpx.Response) -> Optional[float]:
        # Respecte Retry-After (secondes) si present, sinon X-RateLimit-Reset
        # (timestamp epoch). Retourne None si aucune info exploitable.
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), _MAX_RATE_LIMIT_WAIT)
            except ValueError:
                pass
        reset = response.headers.get("X-RateLimit-Reset")
        remaining = response.headers.get("X-RateLimit-Remaining")
        if reset and remaining is not None:
            try:
                if int(remaining) <= 0:
                    delta = float(reset) - time.time()
                    if delta > 0:
                        return min(delta, _MAX_RATE_LIMIT_WAIT)
            except ValueError:
                pass
        return None

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        # Helper de retry: gere rate limit GitHub (403/429), 5xx et erreurs reseau.
        # Ne change pas les signatures publiques; les appelants restent inchanges.
        last_exc: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                if attempt < _MAX_RETRIES - 1:
                    last_exc = exc
                    await asyncio.sleep(_BASE_BACKOFF * (2 ** attempt))
                    continue
                raise

            status = response.status_code
            if status in _RATE_LIMIT_STATUS and attempt < _MAX_RETRIES - 1:
                wait = self._rate_limit_wait(response)
                if wait is not None:
                    await asyncio.sleep(wait)
                    continue
                # 403 sans signal de rate limit: probablement une vraie erreur
                # d'autorisation, on ne retry pas inutilement.
                if status == 429:
                    await asyncio.sleep(_BASE_BACKOFF * (2 ** attempt))
                    continue
                return response
            if status in _RETRYABLE_STATUS and attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_BASE_BACKOFF * (2 ** attempt))
                continue
            return response

        if last_exc is not None:
            raise last_exc
        return response

    async def create_issue(self, owner: str, repo: str, title: str, body: str, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues",
            json={"title": title, "body": body, "labels": labels or []}
        )
        response.raise_for_status()
        return response.json()

    async def close_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        response = await self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/issues/{issue_number}",
            json={"state": "closed"}
        )
        response.raise_for_status()
        return response.json()

    async def create_pull_request(self, owner: str, repo: str, title: str, body: str, head: str, base: str = "main") -> Dict[str, Any]:
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            json={"title": title, "body": body, "head": head, "base": base}
        )
        response.raise_for_status()
        return response.json()

    async def get_default_branch(self, owner: str, repo: str) -> str:
        response = await self._request("GET", f"/repos/{owner}/{repo}")
        response.raise_for_status()
        return response.json().get("default_branch", "main")

    async def get_ref_sha(self, owner: str, repo: str, ref: str) -> str:
        ref_enc = urllib.parse.quote(ref, safe="")
        response = await self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{ref_enc}")
        response.raise_for_status()
        return response.json()["object"]["sha"]

    async def create_branch(self, owner: str, repo: str, branch_name: str, from_ref: Optional[str] = None) -> Dict[str, Any]:
        base = from_ref or await self.get_default_branch(owner, repo)
        sha = await self.get_ref_sha(owner, repo, base)
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": sha}
        )
        response.raise_for_status()
        return response.json()

    async def get_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> Optional[str]:
        # url-encode path (en preservant les / de chemin) et ref.
        path_enc = urllib.parse.quote(path, safe="/")
        ref_enc = urllib.parse.quote(ref, safe="")
        response = await self._request(
            "GET", f"/repos/{owner}/{repo}/contents/{path_enc}?ref={ref_enc}"
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            return None

        content = data.get("content")
        encoding = data.get("encoding")
        if encoding == "base64" and content:
            try:
                return base64.b64decode(content).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                # Fichier binaire ou contenu non decodable proprement.
                return None

        # Fichiers > 1MB: l'API contents renvoie content vide + download_url.
        # On recupere alors le contenu brut via download_url.
        download_url = data.get("download_url")
        if download_url:
            try:
                raw = await self._request("GET", download_url)
                raw.raise_for_status()
            except httpx.HTTPError:
                return None
            try:
                return raw.content.decode("utf-8")
            except UnicodeDecodeError:
                return None
        return None

    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        message: str,
        content: str,
        branch: str,
        sha: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        path_enc = urllib.parse.quote(path, safe="/")
        response = await self._request(
            "PUT", f"/repos/{owner}/{repo}/contents/{path_enc}", json=payload
        )
        response.raise_for_status()
        return response.json()

    async def create_comment(self, owner: str, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body}
        )
        response.raise_for_status()
        return response.json()

    async def list_repo_files(self, owner: str, repo: str, path: str = "", ref: str = "main") -> List[Dict[str, Any]]:
        # NOTE: l'API contents renvoie au max 1000 entrees par dossier (pas de
        # pagination classique pour un listing de dossier). Au-dela, le listing
        # est tronque silencieusement par GitHub.
        path_enc = urllib.parse.quote(path, safe="/")
        ref_enc = urllib.parse.quote(ref, safe="")
        response = await self._request(
            "GET", f"/repos/{owner}/{repo}/contents/{path_enc}?ref={ref_enc}"
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else [data]

    async def close(self):
        await self.client.aclose()
