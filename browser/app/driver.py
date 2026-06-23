import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urlsplit
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class PlaywrightDriver:
    # Borne FIFO du nombre d'entrees conservees pour console_logs et network_requests.
    MAX_CAPTURED_ENTRIES = 1000

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.console_logs: List[Dict[str, Any]] = []
        self.network_requests: List[Dict[str, Any]] = []

    async def start(self, headless: bool = True, video_dir: Optional[str] = None):
        self.playwright = await async_playwright().start()
        try:
            # Args adaptes a l'execution en conteneur Docker:
            # --no-sandbox: le sandbox Chromium ne fonctionne pas dans un conteneur sans
            #   privileges supplementaires (le worker tourne en conteneur).
            # --disable-dev-shm-usage: /dev/shm est souvent trop petit (64Mo) dans Docker,
            #   sans ce flag Chromium crashe par manque de memoire partagee.
            # --disable-gpu: pas de GPU en conteneur headless, evite des erreurs de rendu.
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
            }
            if video_dir:
                os.makedirs(video_dir, exist_ok=True)
                context_options["record_video_dir"] = video_dir
            self.context = await self.browser.new_context(**context_options)
            self.page = await self.context.new_page()
            self._setup_listeners()
        except Exception:
            # Une exception apres async_playwright().start() laisserait des ressources
            # orphelines (process Chromium). On nettoie en best-effort puis on re-raise.
            await self.stop()
            raise

    def _append_bounded(self, target: List[Dict[str, Any]], entry: Dict[str, Any]):
        # Borne FIFO: sur les longues sessions, ces listes croissent sans limite
        # (fuite memoire) et accumulent des donnees potentiellement sensibles.
        # On garde au plus MAX_CAPTURED_ENTRIES entrees, les plus recentes.
        target.append(entry)
        if len(target) > self.MAX_CAPTURED_ENTRIES:
            del target[0]

    def _setup_listeners(self):
        self.page.on("console", lambda msg: self._append_bounded(self.console_logs, {
            "level": msg.type,
            "message": msg.text,
            "url": self.page.url if self.page else "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        self.page.on("request", lambda req: self._append_bounded(self.network_requests, {
            "method": req.method,
            "url": req.url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        self.page.on("response", lambda res: self._append_bounded(self.network_requests, {
            "url": res.url,
            "status": res.status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))

    async def goto(self, url: str, wait_until: str = "load", timeout: int = 30000):
        # wait_until="load" par defaut: plus sur que "networkidle" qui peut ne jamais
        # arriver sur des SPA (polling, websockets) et bloquer le worker indefiniment.
        # timeout borne (30s) garantit qu'un worker ne reste pas coince meme si l'event
        # de chargement attendu ne se declenche jamais.
        await self.page.goto(url, wait_until=wait_until, timeout=timeout)

    async def fill(self, selector: str, value: str):
        await self.page.fill(selector, value)

    async def click(self, selector: str):
        await self.page.click(selector)

    async def screenshot(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        await self.page.screenshot(path=path, full_page=True)

    async def get_links(self) -> List[str]:
        elements = await self.page.query_selector_all("a[href]")
        # Origine de la page courante pour ne garder que les liens internes
        # (relatifs OU absolus de meme origine).
        page_origin = urlsplit(self.page.url)
        links = []
        for el in elements:
            href = await el.get_attribute("href")
            if not href:
                continue
            if href.startswith("/"):
                links.append(href)
                continue
            parts = urlsplit(href)
            # Lien absolu de meme origine (meme scheme + meme host:port).
            if parts.scheme and parts.netloc and (parts.scheme, parts.netloc) == (
                page_origin.scheme,
                page_origin.netloc,
            ):
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
        # Fermetures defensives et INDEPENDANTES: si l'une echoue, les suivantes
        # sont quand meme tentees pour garantir qu'aucun process Chromium ne fuit.
        if self.context:
            try:
                await self.context.close()
            except Exception as e:
                print(f"PlaywrightDriver.stop: context.close failed: {e}")
            finally:
                self.context = None
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                print(f"PlaywrightDriver.stop: browser.close failed: {e}")
            finally:
                self.browser = None
        if getattr(self, "playwright", None):
            try:
                await self.playwright.stop()
            except Exception as e:
                print(f"PlaywrightDriver.stop: playwright.stop failed: {e}")
            finally:
                self.playwright = None
        self.page = None
