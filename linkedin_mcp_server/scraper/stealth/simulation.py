"""Human behavior simulation for LinkedIn interaction patterns."""

import logging
import random

from patchright.async_api import Page

from linkedin_mcp_server.scraper.stealth.controller import PageType
from linkedin_mcp_server.scraper.stealth.profiles import SimulationLevel, StealthProfile

logger = logging.getLogger(__name__)


class InteractionSimulator:
    """Simulate human-like interaction patterns on LinkedIn pages.

    This class provides configurable behavior simulation ranging from none
    to comprehensive, enabling speed vs stealth trade-offs.
    """

    def __init__(self, level: SimulationLevel):
        """Initialize interaction simulator.

        Args:
            level: Simulation level (NONE, BASIC, MODERATE, COMPREHENSIVE)
        """
        self.level = level
        logger.debug(f"InteractionSimulator initialized with level: {level.value}")

    async def simulate_page_interaction(
        self,
        page: Page,
        page_type: PageType,
        profile: StealthProfile,
    ) -> None:
        """Simulate human interaction based on configuration.

        Args:
            page: Patchright page instance
            page_type: Type of LinkedIn page
            profile: Stealth profile for timing configurations
        """
        if self.level == SimulationLevel.NONE:
            logger.debug("Skipping interaction simulation (NONE level)")
            return

        logger.debug(f"Simulating {self.level.value} interaction for {page_type.value}")

        # Route to appropriate simulation based on level
        if self.level == SimulationLevel.BASIC:
            await self._simulate_basic_interaction(page, page_type, profile)
        elif self.level == SimulationLevel.MODERATE:
            await self._simulate_moderate_interaction(page, page_type, profile)
        elif self.level == SimulationLevel.COMPREHENSIVE:
            await self._simulate_comprehensive_interaction(page, page_type, profile)

    async def _simulate_basic_interaction(
        self,
        page: Page,
        page_type: PageType,
        profile: StealthProfile,
    ) -> None:
        """Basic interaction simulation - minimal scrolling and delays.

        This provides basic human-like behavior with minimal performance impact.
        """
        logger.debug("Performing basic interaction simulation")

        try:
            # Simple scroll pattern
            viewport_height = await page.evaluate("window.innerHeight")

            # Scroll down in 2-3 steps
            steps = random.randint(2, 3)
            for i in range(steps):
                scroll_position = (i + 1) * (viewport_height // steps)
                await page.evaluate(f"window.scrollTo(0, {scroll_position})")

                # Brief delay
                delay = random.uniform(*profile.delays.scroll) * 0.5
                await page.wait_for_timeout(int(delay * 1000))

            # Return to top
            await page.evaluate("window.scrollTo(0, 0)")

        except Exception as e:
            logger.debug(f"Basic interaction simulation failed: {e}")

    async def _simulate_moderate_interaction(
        self,
        page: Page,
        page_type: PageType,
        profile: StealthProfile,
    ) -> None:
        """Moderate interaction simulation - balanced behavior patterns.

        This provides a good balance between stealth and performance.
        """
        logger.debug("Performing moderate interaction simulation")

        try:
            # Get page dimensions
            page_height = await page.evaluate("document.body.scrollHeight")

            # Moderate scroll pattern with some mouse movements
            scroll_positions = [0.25, 0.5, 0.75, 1.0, 0.5]

            for position in scroll_positions:
                scroll_to = int(page_height * position)

                # Smooth scroll
                await page.evaluate(
                    f"""
                    window.scrollTo({{
                        top: {scroll_to},
                        behavior: 'smooth'
                    }});
                    """
                )

                # Random delay
                delay = random.uniform(*profile.delays.scroll)
                await page.wait_for_timeout(int(delay * 1000))

                # Occasionally simulate mouse movement
                if random.random() < 0.3:
                    await self._simulate_mouse_movement(page)

            # Focus on specific sections based on page type
            if page_type == PageType.PROFILE:
                await self._focus_on_profile_sections(page, profile, moderate=True)

        except Exception as e:
            logger.debug(f"Moderate interaction simulation failed: {e}")

    async def _simulate_comprehensive_interaction(
        self,
        page: Page,
        page_type: PageType,
        profile: StealthProfile,
    ) -> None:
        """Comprehensive interaction simulation - full behavior patterns.

        This matches the current system's comprehensive scrolling and interaction,
        providing maximum stealth at the cost of performance.
        """
        logger.debug("Performing comprehensive interaction simulation")

        try:
            # Comprehensive scrolling pattern
            await self._comprehensive_scrolling(page, profile)

            # Page-specific interactions
            if page_type == PageType.PROFILE:
                await self._comprehensive_profile_interaction(page, profile)
            elif page_type == PageType.JOB_LISTING:
                await self._comprehensive_job_interaction(page, profile)
            elif page_type == PageType.COMPANY_PAGE:
                await self._comprehensive_company_interaction(page, profile)

            # Final comprehensive scroll
            await self._comprehensive_scrolling(page, profile, final_pass=True)

        except Exception as e:
            logger.debug(f"Comprehensive interaction simulation failed: {e}")

    async def _comprehensive_scrolling(
        self,
        page: Page,
        profile: StealthProfile,
        final_pass: bool = False,
    ) -> None:
        """Perform comprehensive scrolling to trigger all lazy loading."""
        try:
            viewport_height = await page.evaluate("window.innerHeight")

            logger.debug(
                f"Performing {'final' if final_pass else 'initial'} "
                "comprehensive scroll"
            )

            # Gradual scroll down in sections
            scroll_sections = 5 if final_pass else 8
            for i in range(scroll_sections):
                scroll_position = (i + 1) * (viewport_height // scroll_sections)
                await page.evaluate(f"window.scrollTo(0, {scroll_position})")

                # Wait time based on pass type
                wait_mult = 0.5 if final_pass else 1.0
                delay = random.uniform(*profile.delays.scroll) * wait_mult
                await page.wait_for_timeout(int(delay * 1000))

            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            delay = random.uniform(*profile.delays.reading) if not final_pass else 1.0
            await page.wait_for_timeout(int(delay * 1000))

            # Scroll back up gradually
            for i in range(3):
                scroll_ratio = (2 - i) / 3
                await page.evaluate(
                    f"window.scrollTo(0, document.body.scrollHeight * {scroll_ratio})"
                )
                delay = random.uniform(*profile.delays.scroll) * 0.5
                await page.wait_for_timeout(int(delay * 1000))

            # Return to top
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)

        except Exception as e:
            logger.debug(f"Comprehensive scrolling failed: {e}")

    async def _comprehensive_profile_interaction(
        self,
        page: Page,
        profile: StealthProfile,
    ) -> None:
        """Comprehensive interaction for profile pages."""
        section_selectors = [
            ".pv-text-details__left-panel",  # Main profile info
            ".pv-about-section",  # About section
            "section:has(#experience)",  # Experience
            "section:has(#education)",  # Education
            ".pv-accomplishments-section",  # Accomplishments
            ".pv-interests-section",  # Interests
        ]

        for selector in section_selectors:
            try:
                if await page.locator(selector).count() > 0:
                    element = page.locator(selector).first
                    await element.scroll_into_view_if_needed()

                    # Reading delay
                    delay = random.uniform(*profile.delays.reading)
                    await page.wait_for_timeout(int(delay * 1000))

                    # Sometimes hover
                    if random.random() < 0.4:
                        await element.hover()
                        await page.wait_for_timeout(500)

            except Exception as e:
                logger.debug(f"Section interaction failed {selector}: {e}")

    async def _comprehensive_job_interaction(
        self,
        page: Page,
        profile: StealthProfile,
    ) -> None:
        """Comprehensive interaction for job listing pages."""
        # Focus on job description and company info
        job_selectors = [
            ".jobs-description",
            ".jobs-company-box",
            ".jobs-details",
        ]

        for selector in job_selectors:
            try:
                if await page.locator(selector).count() > 0:
                    element = page.locator(selector).first
                    await element.scroll_into_view_if_needed()
                    delay = random.uniform(*profile.delays.reading) * 0.7
                    await page.wait_for_timeout(int(delay * 1000))
            except Exception as e:
                logger.debug(f"Job section interaction failed {selector}: {e}")

    async def _comprehensive_company_interaction(
        self,
        page: Page,
        profile: StealthProfile,
    ) -> None:
        """Comprehensive interaction for company pages."""
        company_selectors = [
            ".org-overview",
            ".org-about-us",
            ".org-people",
        ]

        for selector in company_selectors:
            try:
                if await page.locator(selector).count() > 0:
                    element = page.locator(selector).first
                    await element.scroll_into_view_if_needed()
                    delay = random.uniform(*profile.delays.reading) * 0.8
                    await page.wait_for_timeout(int(delay * 1000))
            except Exception as e:
                logger.debug(f"Company section interaction failed {selector}: {e}")

    async def _focus_on_profile_sections(
        self,
        page: Page,
        profile: StealthProfile,
        moderate: bool = False,
    ) -> None:
        """Focus on specific profile sections with reading simulation."""
        # Select fewer sections for moderate interaction
        section_selectors = [
            ".pv-text-details__left-panel",
            "section:has(#experience)",
            "section:has(#education)",
        ]

        if not moderate:
            section_selectors.extend(
                [
                    ".pv-about-section",
                    ".pv-accomplishments-section",
                    ".pv-interests-section",
                ]
            )

        for selector in section_selectors:
            try:
                if await page.locator(selector).count() > 0:
                    element = page.locator(selector).first
                    await element.scroll_into_view_if_needed()

                    # Shorter delays for moderate interaction
                    mult = 0.5 if moderate else 1.0
                    delay = random.uniform(*profile.delays.reading) * mult
                    await page.wait_for_timeout(int(delay * 1000))

            except Exception as e:
                logger.debug(f"Section focus failed {selector}: {e}")

    async def _simulate_mouse_movement(self, page: Page) -> None:
        """Simulate random mouse movement on the page."""
        try:
            # Get viewport dimensions
            width = await page.evaluate("window.innerWidth")
            height = await page.evaluate("window.innerHeight")

            # Generate random points
            points = []
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, width - 100)
                y = random.randint(100, height - 100)
                points.append((x, y))

            # Move mouse through points
            for x, y in points:
                await page.mouse.move(x, y)
                await page.wait_for_timeout(random.randint(100, 300))

        except Exception as e:
            logger.debug(f"Mouse movement simulation failed: {e}")
