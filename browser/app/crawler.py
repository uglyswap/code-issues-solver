import os
from typing import List, Dict, Any
from urllib.parse import urljoin

from browser.app.driver import PlaywrightDriver


class AppCrawler:
    def __init__(self, driver: PlaywrightDriver, base_url: str, max_pages: int = 20):
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self.max_pages = max_pages
        self.visited: List[str] = []
        self.screenshots: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def _record_error(self, stage: str, exc: Exception, url: str = None):
        # Les echecs ne doivent plus etre avales silencieusement: on les rend
        # visibles (log) ET on les expose dans le resultat pour diagnostic, tout
        # en gardant la robustesse (le crawl continue).
        message = f"{stage} failed{f' on {url}' if url else ''}: {exc}"
        print(message)
        self.errors.append({"stage": stage, "url": url, "error": str(exc)})

    async def run(self, username: str = None, password: str = None) -> Dict[str, Any]:
        await self.driver.goto(self.base_url)
        if username and password:
            try:
                await self._attempt_login(username, password)
            except Exception as e:
                self._record_error("login", e, self.base_url)
        self.visited.append(self.base_url)
        await self._capture_page(self.base_url, 0)

        to_visit = []
        try:
            links = await self.driver.get_links()
            for link in links:
                full = urljoin(self.base_url, link)
                if full not in self.visited and full not in to_visit:
                    to_visit.append(full)
        except Exception as e:
            self._record_error("get_links", e, self.base_url)

        for i, url in enumerate(to_visit[: self.max_pages - 1]):
            try:
                await self.driver.goto(url)
                self.visited.append(url)
                await self._capture_page(url, i + 1)
            except Exception as e:
                self._record_error("visit_page", e, url)

        broken = await self.driver.find_broken_elements()

        return {
            "pages_visited": self.visited,
            "screenshots": self.screenshots,
            "console_logs": self.driver.console_logs,
            "network_requests": self.driver.network_requests,
            "broken_elements": broken,
            "errors": self.errors,
        }

    async def _attempt_login(self, username: str, password: str):
        page = self.driver.page
        # Heuristic login form detection
        selectors = [
            'input[type="text"]',
            'input[type="email"]',
            'input[name="username"]',
            'input[name="user"]',
            'input[id="username"]',
        ]
        user_input = None
        for sel in selectors:
            if await page.query_selector(sel):
                user_input = sel
                break
        pass_input = 'input[type="password"]'
        submit = 'button[type="submit"], input[type="submit"]'
        if user_input:
            await page.fill(user_input, username)
            await page.fill(pass_input, password)
            await page.click(submit)
            await page.wait_for_load_state("networkidle")

    async def _capture_page(self, url: str, index: int):
        from datetime import datetime, timezone
        # %f (microsecondes) en plus de l'index pour eviter l'ecrasement de captures
        # prises dans la meme seconde (le timestamp a la seconde collisionnait).
        path = f"screenshots/page_{index}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}.png"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        await self.driver.screenshot(path)
        self.screenshots.append({
            "url": url,
            "path": path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
