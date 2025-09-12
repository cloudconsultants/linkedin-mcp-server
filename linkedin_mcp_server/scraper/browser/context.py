"""Simple browser management for LinkedIn scraping."""

import os
import logging
from pathlib import Path
from playwright.async_api import BrowserContext, async_playwright

from ..config import BrowserConfig

logger = logging.getLogger(__name__)


class BrowserContextManager:
    """Context manager for browser contexts with storage state support."""

    def __init__(self, headless: bool = True, storage_state_path: str | None = None):
        self.headless = headless
        self.storage_state_path = storage_state_path
        self.playwright_context = None
        self.context = None

    async def __aenter__(self) -> BrowserContext:
        """Create browser context with storage state if available."""
        self.playwright_context = async_playwright()
        playwright = await self.playwright_context.__aenter__()

        browser = await playwright.chromium.launch(
            headless=self.headless,
            args=BrowserConfig.CHROME_ARGS,
        )

        context_options = {
            "user_agent": BrowserConfig.USER_AGENT,
            "viewport": BrowserConfig.VIEWPORT,
        }

        # Load storage state if available
        if self.storage_state_path and os.path.exists(self.storage_state_path):
            context_options["storage_state"] = self.storage_state_path
            logger.info(f"Loading storage state from {self.storage_state_path}")

        self.context = await browser.new_context(**context_options)
        self.context.set_default_timeout(BrowserConfig.TIMEOUT)

        return self.context

    async def save_storage_state(self):
        """Save authentication state for reuse."""
        if self.storage_state_path and self.context:
            # Ensure directory exists
            Path(self.storage_state_path).parent.mkdir(parents=True, exist_ok=True)
            await self.context.storage_state(path=self.storage_state_path)
            logger.info(f"Saved storage state to {self.storage_state_path}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Save state before cleanup."""
        try:
            if self.context:
                await self.save_storage_state()
        except Exception as e:
            logger.warning(f"Failed to save storage state: {e}")

        # Original cleanup
        if self.playwright_context:
            await self.playwright_context.__aexit__(exc_type, exc_val, exc_tb)
