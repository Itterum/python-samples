import asyncio
from typing import TypeVar, Generic, Optional, List, Dict, Any
from abc import ABC, abstractmethod
from datetime import datetime
import pytz
from playwright.async_api import ElementHandle, Page, Browser, async_playwright

T = TypeVar("T")


class AbstractEntity(Generic[T], ABC):
    fields: T
    collected: dict[str, str]

    def __init__(self, fields: T):
        self.fields = fields
        self.collected = {"date": self.format_date(datetime.now())}

    def get_info(self):
        return {"fields": self.fields, "collected": self.collected}

    @staticmethod
    def format_date(date: datetime, timezone: str = "Europe/Moscow") -> str:
        tz = pytz.timezone(timezone)
        return date.astimezone(tz).isoformat()


class AbstractExtractor(Generic[T], ABC):
    wait_selector: str
    domain: str

    def __init__(self):
        self._playwright = None

    @abstractmethod
    async def parse_entity(self, element: ElementHandle) -> T:
        pass

    @staticmethod
    async def setup_page(page: Page, blocked_resources: Optional[List[str]] = None) -> None:
        if blocked_resources is None:
            blocked_resources = ["image", "stylesheet", "font", "media", "script"]

        async def route_handler(route):
            request = route.request
            resource_type = request.resource_type
            headers = request.headers

            if resource_type in blocked_resources:
                await route.abort()
                return

            referer = headers.get("referer", "")
            if "ads.example.com" in referer:
                await route.abort()
                return

            await route.continue_()

        await page.route("**/*", route_handler)

        await page.add_init_script("""
            Object.defineProperty(navigator, "webdriver", { get: () => false });
            Object.defineProperty(window, "chrome", { get: () => ({ runtime: {} }) });
            Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3, 4, 5] });
        """)

        async def realistic_mouse_move():
            await page.mouse.move(100, 100, steps=20)
            await page.mouse.move(300, 200, steps=15)

        await page.expose_function("realisticMouseMove", realistic_mouse_move)

        cdp = await page.context.new_cdp_session(page)
        await cdp.send("Network.setUserAgentOverride", {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })

        await page.mouse.move(100, 100, steps=10)
        await page.mouse.move(250, 200, steps=15)

    async def launch_browser(self, headless: bool = True, proxy: Optional[str] = None) -> Browser:
        self._playwright = await async_playwright().start()
        return await self._playwright.chromium.launch(
            headless=headless,
            proxy={"server": proxy} if proxy else None,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

    async def parse_page(self, url: str, options: Optional[Dict[str, Any]] = None) -> List[T]:
        if options is None:
            options = {}

        browser = await self.launch_browser(options.get("headless", True), options.get("proxy"))
        page = await browser.new_page()
        results = []

        try:
            await self.setup_page(page)
            await self.log_requests(page, options.get("proxy"))

            await page.goto(url, wait_until="domcontentloaded")

            await page.screenshot(
                path="../screenshots/screenshot_after_load.png",
                full_page=True,
                animations="disabled"
            )

            await page.screenshot(path="../screenshots/viewport_screenshot.png")

            await page.wait_for_selector(self.wait_selector)
            elements = await page.query_selector_all(self.wait_selector)
            results = await asyncio.gather(*(self.parse_entity(element) for element in elements))
        except Exception as e:
            print("Error during page parsing:", e)
        finally:
            await page.close()
            await browser.close()
            await self._playwright.stop()
            return results

    @staticmethod
    async def log_requests(page: Page, proxy: Optional[str] = None) -> None:
        async def on_request(request):
            request_info = {
                "url"      : request.url,
                "method"   : request.method,
                "headers"  : await request.all_headers(),
                "proxyUsed": proxy
            }
            print("Request Info:", request_info)

        page.on("request", on_request)

    @staticmethod
    async def scroll_to_end(page: Page, max_attempts: int = 10, delay_ms: int = 2000) -> None:
        for _ in range(max_attempts):
            previous_height = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(delay_ms / 1000)
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                break
