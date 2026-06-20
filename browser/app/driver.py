import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class PlaywrightDriver:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.console_logs: List[Dict[str, Any]] = []
        self.network_requests: List[Dict[str, Any]] = []

    async def start(self, headless: bool = True, video_dir: Optional[str] = None):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
        }
        if video_dir:
            os.makedirs(video_dir, exist_ok=True)
            context_options["record_video_dir"] = video_dir
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        self._setup_listeners()

    def _setup_listeners(self):
        self.page.on("console", lambda msg: self.console_logs.append({
            "level": msg.type,
            "message": msg.text,
            "url": self.page.url if self.page else "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        self.page.on("request", lambda req: self.network_requests.append({
            "method": req.method,
            "url": req.url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        self.page.on("response", lambda res: self.network_requests.append({
            "url": res.url,
            "status": res.status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))

    async def goto(self, url: str, wait_until: str = "networkidle"):
        await self.page.goto(url, wait_until=wait_until)

    async def fill(self, selector: str, value: str):
        await self.page.fill(selector, value)

    async def click(self, selector: str):
        await self.page.click(selector)

    async def screenshot(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        await self.page.screenshot(path=path, full_page=True)

    async def get_links(self) -> List[str]:
        elements = await self.page.query_selector_all("a[href]")
        links = []
        for el in elements:
            href = await el.get_attribute("href")
            if href and href.startswith("/"):
                links.append(href)
        return list(dict.fromkeys(links))

    async def get_visible_text(self) -> str:
        return await self.page.inner_text("body")

    async def find_broken_elements(self) -> List[Dict[str, Any]]:
        broken = []
        # Check for buttons with no click handler or visually hidden
        buttons = await self.page.query_selector_all("button")
        for btn in buttons:
            if await btn.is_visible():
                box = await btn.bounding_box()
                if box and (box["width"] == 0 or box["height"] == 0):
                    broken.append({"type": "button", "tag": "button", "reason": "zero_size"})
        # Check for images without src or broken
        images = await self.page.query_selector_all("img")
        for img in images:
            src = await img.get_attribute("src")
            if not src:
                broken.append({"type": "image", "tag": "img", "reason": "missing_src"})
        return broken

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, "playwright"):
            await self.playwright.stop()
