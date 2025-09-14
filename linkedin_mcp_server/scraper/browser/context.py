"""Stealth-enhanced browser management for LinkedIn scraping."""

import logging
from pathlib import Path
from typing import Optional
from patchright.async_api import BrowserContext, Page

from ..config import StealthConfig, LinkedInDetectionError
from .stealth_manager import StealthManager
from .behavioral import warm_linkedin_session, simulate_profile_reading_behavior

logger = logging.getLogger(__name__)


class StealthBrowserContextManager:
    """Stealth-enhanced context manager for LinkedIn scraping with session warming."""

    def __init__(
        self,
        headless: bool = True,
        storage_state_path: Optional[str] = None,
        stealth_config: Optional[StealthConfig] = None,
        enable_session_warming: bool = True,
    ):
        self.headless = headless
        self.storage_state_path = storage_state_path
        self.stealth_config = stealth_config or StealthConfig(headless=headless)
        self.enable_session_warming = enable_session_warming
        self.stealth_manager = StealthManager(self.stealth_config)
        self.context: Optional[BrowserContext] = None
        self.warmed_up = False

    async def __aenter__(self) -> BrowserContext:
        """Create stealth browser context with optional session warming."""
        logger.info("Creating stealth browser context...")

        try:
            # Create stealth context using the manager
            self.context = await self.stealth_manager.create_stealth_context(
                self.storage_state_path
            )

            # Perform session warming if enabled
            if self.enable_session_warming and not self.warmed_up:
                await self.warm_session()
                self.warmed_up = True

            return self.context

        except Exception as e:
            logger.error(f"Failed to create stealth context: {e}")
            await self.cleanup()
            raise LinkedInDetectionError(f"Context creation failed: {e}")

    async def warm_session(self):
        """Warm up the session to avoid detection."""
        if not self.context:
            raise RuntimeError("Context not initialized")

        logger.info("Warming LinkedIn session...")
        page = await self.context.new_page()

        try:
            await warm_linkedin_session(page, self.stealth_config)
            logger.info("Session warming completed successfully")
        except Exception as e:
            logger.error(f"Session warming failed: {e}")
            raise
        finally:
            await page.close()

    async def create_stealth_page(self) -> Page:
        """Create a new page with stealth behaviors ready."""
        if not self.context:
            raise RuntimeError("Context not initialized")

        page = await self.context.new_page()

        # Set up page-level stealth behaviors
        await self._setup_page_stealth(page)

        return page

    async def _setup_page_stealth(self, page: Page):
        """Set up page-level stealth configurations."""
        try:
            # Override navigator.webdriver
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)

            # Set up request interception for additional stealth
            async def handle_route(route):
                # Add random delays to requests to seem more human
                import asyncio
                import random

                await asyncio.sleep(random.uniform(0.01, 0.1))
                await route.continue_()

            # Intercept some requests to add delays
            await page.route("**/*", handle_route)

        except Exception as e:
            logger.debug(f"Page stealth setup failed: {e}")

    async def navigate_to_profile_safely(self, page: Page, linkedin_url: str) -> bool:
        """Safely navigate to a LinkedIn profile with stealth patterns."""
        try:
            # Enforce rate limiting first
            await self.stealth_manager.enforce_rate_limit()

            # Import here to avoid circular imports
            from .behavioral import (
                navigate_to_profile_stealthily,
                detect_linkedin_challenge,
            )

            # Navigate using stealth patterns
            await navigate_to_profile_stealthily(
                page, linkedin_url, self.stealth_config
            )

            # Check for detection after navigation
            if await detect_linkedin_challenge(page):
                raise LinkedInDetectionError(
                    "Detection suspected after profile navigation"
                )

            # Simulate human reading behavior
            await simulate_profile_reading_behavior(page, self.stealth_config)

            return True

        except LinkedInDetectionError as e:
            logger.error(f"LinkedIn detection during navigation: {e}")
            await self.stealth_manager.handle_detection(page, e)
            return False
        except Exception as e:
            logger.error(f"Profile navigation failed: {e}")
            return False

    async def save_storage_state(self):
        """Save authentication state for reuse."""
        if self.storage_state_path and self.context:
            try:
                # Ensure directory exists
                Path(self.storage_state_path).parent.mkdir(parents=True, exist_ok=True)
                await self.context.storage_state(path=self.storage_state_path)
                logger.info(f"Saved storage state to {self.storage_state_path}")
            except Exception as e:
                logger.warning(f"Failed to save storage state: {e}")

    async def cleanup(self):
        """Clean up stealth resources."""
        try:
            if self.context:
                await self.save_storage_state()

            await self.stealth_manager.cleanup()
            self.context = None
            self.warmed_up = False

        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context exit."""
        await self.cleanup()


# Backward compatibility alias
BrowserContextManager = StealthBrowserContextManager
