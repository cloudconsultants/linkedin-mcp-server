"""Stealth library management for LinkedIn scraping."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Browser

from ..config import BrowserConfig, StealthConfig, LinkedInDetectionError

logger = logging.getLogger(__name__)


class StealthManager:
    """Manages stealth library selection and configuration with fallback support."""
    
    def __init__(self, config: Optional[StealthConfig] = None):
        self.config = config or StealthConfig()
        self.profiles_scraped = 0
        self.last_profile_time = 0.0
        self.current_browser: Optional[Browser] = None
        self.playwright_instance = None
        
    async def create_stealth_context(self, storage_state_path: Optional[str] = None) -> BrowserContext:
        """Create stealth browser context with fallback."""
        logger.info("Creating stealth browser context...")
        
        try:
            if self.config.use_patchright:
                return await self._create_patchright_context(storage_state_path)
        except Exception as e:
            logger.warning(f"Patchright failed: {e}")
            if self.config.fallback_to_botright:
                logger.info("Falling back to Botright...")
                return await self._create_botright_context(storage_state_path)
            raise
            
        # This should never be reached, but ensures all paths return BrowserContext
        logger.warning("Unexpected path in create_stealth_context, using fallback")
        return await self._create_fallback_playwright_context(storage_state_path)
            
    async def _create_patchright_context(self, storage_state_path: Optional[str] = None) -> BrowserContext:
        """Create browser context using Patchright for stealth."""
        try:
            # Import patchright dynamically to handle installation issues gracefully
            from patchright.async_api import async_playwright
            logger.info("Using Patchright for stealth browsing")
        except ImportError as e:
            logger.error(f"Patchright not available: {e}")
            raise
            
        # Create Playwright instance
        self.playwright_instance = async_playwright()
        playwright = await self.playwright_instance.start()
        
        # Browser launch arguments for stealth
        launch_args = {
            "headless": self.config.headless,
            "channel": "chrome",  # CRITICAL: Use real Chrome, not Chromium
            "args": (
                BrowserConfig.HEADLESS_STEALTH_ARGS 
                if self.config.headless 
                else BrowserConfig.STEALTH_CHROME_ARGS
            ),
        }
        
        # Launch browser with stealth configuration
        self.current_browser = await playwright.chromium.launch(**launch_args)
        
        # Create context with stealth options
        context_options = {
            "user_agent": BrowserConfig.get_user_agent(),
            "viewport": BrowserConfig.VIEWPORT,
        }
        
        # Load storage state if available
        if storage_state_path and Path(storage_state_path).exists():
            context_options["storage_state"] = storage_state_path
            logger.info(f"Loading storage state from {storage_state_path}")
            
        context = await self.current_browser.new_context(**context_options)
        context.set_default_timeout(BrowserConfig.TIMEOUT)
        
        # Inject stealth scripts if needed
        await self._inject_stealth_scripts(context)
        
        return context
        
    async def _create_botright_context(self, storage_state_path: Optional[str] = None) -> BrowserContext:
        """Create browser context using Botright as fallback."""
        try:
            import botright  # type: ignore  # Optional dependency with conflict resolution
            logger.info("Using Botright for stealth browsing")
        except ImportError as e:
            logger.error(f"Botright not available (dependency conflict resolved by using Patchright only): {e}")
            # Fallback to regular Playwright with stealth configuration
            return await self._create_fallback_playwright_context(storage_state_path)
            
        # Botright configuration
        botright_browser = await botright.Botright(
            headless=self.config.headless,
            user_data_dir="./linkedin_browser_data",
        )
        
        # Create new page/context
        page = await botright_browser.new_page()
        context = page.context
        
        # Load storage state if available
        if storage_state_path and Path(storage_state_path).exists():
            with open(storage_state_path, 'r') as f:
                import json
                storage_state = json.load(f)
                await context.add_cookies(storage_state.get('cookies', []))
                logger.info(f"Loaded storage state from {storage_state_path}")
        
        context.set_default_timeout(BrowserConfig.TIMEOUT)
        
        return context
        
    async def _create_fallback_playwright_context(self, storage_state_path: Optional[str] = None) -> BrowserContext:
        """Create browser context using regular Playwright with maximum stealth configuration."""
        try:
            from playwright.async_api import async_playwright
            logger.info("Using fallback Playwright with stealth configuration")
        except ImportError as e:
            logger.error(f"Playwright not available: {e}")
            raise
            
        # Create Playwright instance
        self.playwright_instance = async_playwright()
        playwright = await self.playwright_instance.start()
        
        # Browser launch arguments for maximum stealth
        launch_args = {
            "headless": self.config.headless,
            "args": (
                BrowserConfig.HEADLESS_STEALTH_ARGS 
                if self.config.headless 
                else BrowserConfig.STEALTH_CHROME_ARGS
            ),
        }
        
        # Launch browser with stealth configuration
        self.current_browser = await playwright.chromium.launch(**launch_args)
        
        # Create context with stealth options
        context_options = {
            "user_agent": BrowserConfig.get_user_agent(),
            "viewport": BrowserConfig.VIEWPORT,
        }
        
        # Load storage state if available
        if storage_state_path and Path(storage_state_path).exists():
            context_options["storage_state"] = storage_state_path
            logger.info(f"Loading storage state from {storage_state_path}")
            
        context = await self.current_browser.new_context(**context_options)
        context.set_default_timeout(BrowserConfig.TIMEOUT)
        
        # Inject stealth scripts
        await self._inject_stealth_scripts(context)
        
        return context
        
    async def _inject_stealth_scripts(self, context: BrowserContext):
        """Inject additional stealth scripts to avoid detection."""
        # Remove webdriver property
        stealth_script = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mock chrome runtime
        window.chrome = {
            runtime: {},
        };
        
        // Mock permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Mock plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        // Mock languages  
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        """
        
        await context.add_init_script(stealth_script)
        logger.debug("Injected stealth scripts")
        
    async def enforce_rate_limit(self):
        """Enforce rate limiting (1 profile per minute)."""
        current_time = time.time()
        time_since_last = current_time - self.last_profile_time
        
        if time_since_last < 60:  # Less than 60 seconds since last profile
            wait_time = 60 - time_since_last
            if self.config.stealth_wait_message:
                logger.info(f"Rate limiting: waiting {wait_time:.1f}s before next profile")
            await asyncio.sleep(wait_time)
            
        self.last_profile_time = time.time()
        self.profiles_scraped += 1
        
        # Check if we need to rotate session
        if self.profiles_scraped >= self.config.session_rotation_threshold:
            logger.info("Session rotation threshold reached, will create new session")
            await self.cleanup()
            self.profiles_scraped = 0
            
    async def detect_linkedin_challenge(self, page) -> bool:
        """Detect if LinkedIn is presenting a security challenge."""
        url = page.url.lower()
        
        # Check for challenge URLs
        challenge_indicators = [
            "challenge",
            "checkpoint", 
            "security",
            "verify",
            "captcha",
            "blocked",
        ]
        
        if any(indicator in url for indicator in challenge_indicators):
            logger.warning(f"LinkedIn challenge detected: {page.url}")
            return True
            
        # Check for challenge content
        try:
            challenge_selectors = [
                '[data-test-id*="challenge"]',
                '[class*="challenge"]',
                '[class*="security"]',
                'text="Please complete this security check"',
                'text="We want to make sure it\'s really you"',
            ]
            
            for selector in challenge_selectors:
                if await page.locator(selector).count() > 0:
                    logger.warning(f"Challenge element found: {selector}")
                    return True
                    
        except Exception as e:
            logger.debug(f"Error checking for challenges: {e}")
            
        return False
        
    async def handle_detection(self, page, error: Exception):
        """Handle detection and attempt recovery."""
        logger.error(f"Detection suspected: {error}")
        
        # Check for challenges
        if await self.detect_linkedin_challenge(page):
            raise LinkedInDetectionError("LinkedIn security challenge detected")
            
        # Check for session invalidation
        try:
            await page.wait_for_selector('[data-test-id="login-form"]', timeout=5000)
            logger.error("Session appears to be invalidated - login form detected")
            raise LinkedInDetectionError("LinkedIn session invalidated")
        except Exception:
            pass  # No login form, continue with other checks
            
        # Additional detection patterns
        if page.url == "https://www.linkedin.com/":
            # Sometimes LinkedIn redirects to home without login when detected
            logger.warning("Redirected to home page - possible soft detection")
            
    async def cleanup(self):
        """Clean up browser resources."""
        try:
            if self.current_browser:
                await self.current_browser.close()
                self.current_browser = None
                
            if self.playwright_instance:
                await self.playwright_instance.stop()
                self.playwright_instance = None
                
            logger.debug("Stealth manager cleaned up")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")