import base64
import httpx
from typing import Optional, List, Dict, Any


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

    async def create_issue(self, owner: str, repo: str, title: str, body: str, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        response = await self.client.post(
            f"/repos/{owner}/{repo}/issues",
            json={"title": title, "body": body, "labels": labels or []}
        )
        response.raise_for_status()
        return response.json()

    async def close_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        response = await self.client.patch(
            f"/repos/{owner}/{repo}/issues/{issue_number}",
            json={"state": "closed"}
        )
        response.raise_for_status()
        return response.json()

    async def create_pull_request(self, owner: str, repo: str, title: str, body: str, head: str, base: str = "main") -> Dict[str, Any]:
        response = await self.client.post(
            f"/repos/{owner}/{repo}/pulls",
            json={"title": title, "body": body, "head": head, "base": base}
        )
        response.raise_for_status()
        return response.json()

    async def get_default_branch(self, owner: str, repo: str) -> str:
        response = await self.client.get(f"/repos/{owner}/{repo}")
        response.raise_for_status()
        return response.json().get("default_branch", "main")

    async def get_ref_sha(self, owner: str, repo: str, ref: str) -> str:
        response = await self.client.get(f"/repos/{owner}/{repo}/git/ref/heads/{ref}")
        response.raise_for_status()
        return response.json()["object"]["sha"]

    async def create_branch(self, owner: str, repo: str, branch_name: str, from_ref: Optional[str] = None) -> Dict[str, Any]:
        base = from_ref or await self.get_default_branch(owner, repo)
        sha = await self.get_ref_sha(owner, repo, base)
        response = await self.client.post(
            f"/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": sha}
        )
        response.raise_for_status()
        return response.json()

    async def get_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> Optional[str]:
        response = await self.client.get(f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8")
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
        response = await self.client.put(f"/repos/{owner}/{repo}/contents/{path}", json=payload)
        response.raise_for_status()
        return response.json()

    async def create_comment(self, owner: str, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        response = await self.client.post(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body}
        )
        response.raise_for_status()
        return response.json()

    async def list_repo_files(self, owner: str, repo: str, path: str = "", ref: str = "main") -> List[Dict[str, Any]]:
        response = await self.client.get(f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
        if response.status_code == 404:
            return []
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else [data]

    async def close(self):
        await self.client.aclose()
