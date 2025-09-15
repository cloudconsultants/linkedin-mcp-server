"""Intelligent content loading detection to replace hardcoded waits."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, List

from patchright.async_api import Page

from linkedin_mcp_server.scraper.stealth.controller import ContentTarget
from linkedin_mcp_server.scraper.stealth.profiles import StealthProfile

logger = logging.getLogger(__name__)


@dataclass
class ContentLoadResult:
    """Result of content loading operation."""

    success: bool
    loaded_targets: List[ContentTarget]
    missing_targets: List[ContentTarget]
    load_time: float


class LazyLoadDetector:
    """Smart content loading detection replacing hardcoded waits.

    This class provides intelligent detection of dynamically loaded content,
    eliminating the need for fixed wait times and dramatically improving performance.
    """

    # Content target to selector mappings
    CONTENT_SELECTORS: Dict[ContentTarget, List[str]] = {
        # Profile content
        ContentTarget.BASIC_INFO: [
            ".pv-text-details__left-panel",
            "h1.text-heading-xlarge",
            ".pv-text-details__right-panel",
            ".ph5.pb5",
        ],
        ContentTarget.EXPERIENCE: [
            "#experience",
            "section:has(#experience)",
            ".pv-profile-section__card-item-v2",
            '[data-section="experience"]',
        ],
        ContentTarget.EDUCATION: [
            "#education",
            "section:has(#education)",
            ".pv-education-entity",
            '[data-section="education"]',
        ],
        ContentTarget.SKILLS: [
            "#skills",
            "section:has(#skills)",
            ".pv-skill-entity",
            '[data-section="skills"]',
        ],
        ContentTarget.ACCOMPLISHMENTS: [
            ".pv-accomplishments-section",
            "#accomplishments",
            "section:has(#accomplishments)",
        ],
        ContentTarget.CONTACTS: [
            ".pv-contact-info",
            "#contact-info",
            '[aria-label*="contact info"]',
        ],
        ContentTarget.INTERESTS: [
            ".pv-interests-section",
            "#interests",
            "section:has(#interests)",
        ],
        # Job content (future)
        ContentTarget.JOB_DESCRIPTION: [
            ".jobs-description",
            ".jobs-box__html-content",
            '[data-test-id="job-description"]',
        ],
        ContentTarget.COMPANY_INFO: [
            ".jobs-company",
            ".jobs-company-box",
            '[data-test-id="company-info"]',
        ],
        # Company content (future)
        ContentTarget.COMPANY_OVERVIEW: [
            ".org-overview",
            ".org-about-us",
            '[data-test-id="company-overview"]',
        ],
        ContentTarget.EMPLOYEES: [
            ".org-people",
            ".org-employees",
            '[data-test-id="company-employees"]',
        ],
    }

    # Scroll strategies for different content patterns
    SCROLL_STRATEGIES = {
        "profile": [
            {"position": 0.25, "wait": 0.8},
            {"position": 0.5, "wait": 1.0},
            {"position": 0.75, "wait": 1.2},
            {"position": 1.0, "wait": 1.5},
            {"position": 0.5, "wait": 0.5},  # Return to middle
        ],
        "job": [
            {"position": 0.33, "wait": 0.6},
            {"position": 0.66, "wait": 0.8},
            {"position": 1.0, "wait": 1.0},
        ],
        "company": [
            {"position": 0.25, "wait": 0.7},
            {"position": 0.5, "wait": 0.9},
            {"position": 0.75, "wait": 1.1},
            {"position": 1.0, "wait": 1.3},
        ],
    }

    async def ensure_content_loaded(
        self,
        page: Page,
        targets: List[ContentTarget],
        profile: StealthProfile,
        max_wait_time: int = 30,
    ) -> ContentLoadResult:
        """Intelligently load content instead of blind waiting.

        This method replaces hardcoded waits with smart detection of content loading,
        achieving significant speed improvements.

        Args:
            page: Patchright page instance
            targets: List of content sections to load
            profile: Stealth profile for timing configurations
            max_wait_time: Maximum time to wait for content

        Returns:
            ContentLoadResult with loaded and missing targets
        """
        start_time = time.time()
        loaded_targets = set()

        logger.debug(f"Ensuring content loaded for {len(targets)} targets")

        # Phase 1: Check what's already loaded
        for target in targets:
            if await self._is_content_loaded(page, target):
                loaded_targets.add(target)
                logger.debug(f"Target {target.value} already loaded")

        if len(loaded_targets) == len(targets):
            return ContentLoadResult(
                success=True,
                loaded_targets=list(loaded_targets),
                missing_targets=[],
                load_time=0,
            )

        # Phase 2: Smart scrolling to trigger lazy loading
        missing_targets = [t for t in targets if t not in loaded_targets]
        logger.debug(f"Missing targets: {[t.value for t in missing_targets]}")

        scroll_strategy = self._get_scroll_strategy(missing_targets)
        await self._execute_scroll_strategy(page, scroll_strategy, profile)

        # Phase 3: Monitor for content appearance
        check_interval = 0.5
        checks_performed = 0
        max_checks = int(max_wait_time / check_interval)

        while (time.time() - start_time) < max_wait_time and missing_targets:
            newly_loaded = []

            for target in missing_targets:
                if await self._is_content_loaded(page, target):
                    newly_loaded.append(target)
                    loaded_targets.add(target)
                    logger.debug(
                        f"Target {target.value} loaded after {time.time() - start_time:.1f}s"
                    )

            for target in newly_loaded:
                missing_targets.remove(target)

            if not missing_targets:
                break

            # Progressive backoff for checking
            checks_performed += 1
            if checks_performed > max_checks / 2:
                check_interval = min(check_interval * 1.2, 2.0)

            await asyncio.sleep(check_interval)

        load_time = time.time() - start_time
        success = len(missing_targets) == 0

        if missing_targets:
            logger.warning(
                f"Failed to load {len(missing_targets)} targets after {load_time:.1f}s: "
                f"{[t.value for t in missing_targets]}"
            )
        else:
            logger.info(f"All content loaded in {load_time:.1f}s")

        return ContentLoadResult(
            success=success,
            loaded_targets=list(loaded_targets),
            missing_targets=missing_targets,
            load_time=load_time,
        )

    async def _is_content_loaded(self, page: Page, target: ContentTarget) -> bool:
        """Check if a specific content target is loaded on the page."""
        selectors = self.CONTENT_SELECTORS.get(target, [])

        for selector in selectors:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    # Additional check for content visibility
                    first_element = page.locator(selector).first
                    is_visible = await first_element.is_visible()
                    if is_visible:
                        return True
            except Exception as e:
                logger.debug(f"Error checking selector {selector}: {e}")
                continue

        return False

    def _get_scroll_strategy(self, missing_targets: List[ContentTarget]) -> List[Dict]:
        """Determine optimal scroll strategy based on missing content."""
        # Determine page type from targets
        if any(
            t in [ContentTarget.BASIC_INFO, ContentTarget.EXPERIENCE]
            for t in missing_targets
        ):
            return self.SCROLL_STRATEGIES["profile"]
        elif ContentTarget.JOB_DESCRIPTION in missing_targets:
            return self.SCROLL_STRATEGIES["job"]
        elif ContentTarget.COMPANY_OVERVIEW in missing_targets:
            return self.SCROLL_STRATEGIES["company"]
        else:
            # Default to profile strategy
            return self.SCROLL_STRATEGIES["profile"]

    async def _execute_scroll_strategy(
        self,
        page: Page,
        strategy: List[Dict],
        profile: StealthProfile,
    ) -> None:
        """Execute a scroll strategy to trigger lazy loading."""
        logger.debug(f"Executing scroll strategy with {len(strategy)} steps")

        try:
            # Get page height for calculating positions
            page_height = await page.evaluate("document.body.scrollHeight")

            for step in strategy:
                position = step["position"]
                wait_time = step["wait"]

                # Adjust wait time based on profile
                if profile.simulation.value == "none":
                    wait_time *= 0.2
                elif profile.simulation.value == "basic":
                    wait_time *= 0.5
                elif profile.simulation.value == "moderate":
                    wait_time *= 0.75

                # Calculate scroll position
                if position <= 1.0:
                    # Position as percentage
                    scroll_to = int(page_height * position)
                else:
                    # Absolute position
                    scroll_to = int(position)

                # Smooth scroll simulation
                await page.evaluate(
                    f"""
                    window.scrollTo({{
                        top: {scroll_to},
                        behavior: 'smooth'
                    }});
                    """
                )

                # Wait for content to load
                await asyncio.sleep(wait_time)

                # Update page height (in case it changed due to lazy loading)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height > page_height:
                    logger.debug(
                        f"Page height increased: {page_height} -> {new_height}"
                    )
                    page_height = new_height

        except Exception as e:
            logger.error(f"Error executing scroll strategy: {e}")

    async def wait_for_specific_content(
        self,
        page: Page,
        selector: str,
        timeout: int = 10,
    ) -> bool:
        """Wait for specific content to appear on the page.

        This is a utility method for waiting for specific elements,
        replacing hardcoded wait_for_timeout calls.
        """
        try:
            await page.wait_for_selector(
                selector,
                state="visible",
                timeout=timeout * 1000,
            )
            return True
        except Exception:
            return False
