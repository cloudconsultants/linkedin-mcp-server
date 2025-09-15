"""Decorator system for clean integration of stealth operations."""

import functools
import logging
from typing import Any, Callable, List, Optional, TypeVar

from patchright.async_api import Page

from linkedin_mcp_server.scraper.stealth.controller import (
    ContentTarget,
    PageType,
    StealthController,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def stealth_controlled(
    page_type: PageType,
    content_targets: Optional[List[ContentTarget]] = None,
    use_legacy_fallback: bool = True,
) -> Callable[[F], F]:
    """Decorator to enable centralized stealth control for scraping functions.

    This decorator automatically handles navigation, content loading, and interaction
    simulation using the centralized StealthController, eliminating the need for
    scattered stealth calls in scraping functions.

    Args:
        page_type: Type of LinkedIn page being scraped
        content_targets: List of content sections to ensure are loaded
        use_legacy_fallback: Whether to fall back to legacy stealth on failure

    Example:
        @stealth_controlled(PageType.PROFILE, [ContentTarget.BASIC_INFO, ContentTarget.EXPERIENCE])
        async def scrape_profile(page: Page, url: str) -> Person:
            # Navigation and content loading handled automatically
            # Just extract the data
            return extract_profile_data(page)
    """
    if content_targets is None:
        content_targets = []

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract page and url from arguments
            page = None
            url = None

            # Try to find page and url in arguments
            for arg in args:
                if isinstance(arg, Page):
                    page = arg
                elif isinstance(arg, str) and (
                    "linkedin.com" in arg or arg.startswith("http")
                ):
                    url = arg

            # Check keyword arguments
            if page is None:
                page = kwargs.get("page")
            if url is None:
                url = kwargs.get("url") or kwargs.get("linkedin_url")

            if page is None:
                logger.warning(
                    "No Page instance found in arguments, skipping stealth control"
                )
                return await func(*args, **kwargs)

            if url is None:
                logger.warning("No URL found in arguments, skipping stealth control")
                return await func(*args, **kwargs)

            # Create stealth controller
            controller = StealthController.from_config()

            try:
                # Perform centralized stealth operation
                await controller.scrape_linkedin_page(
                    page=page,
                    url=url,
                    page_type=page_type,
                    content_targets=content_targets,
                )

                # Call original function (stealth already handled)
                return await func(*args, **kwargs)

            except Exception as e:
                if use_legacy_fallback:
                    logger.warning(
                        f"Stealth control failed ({e}), falling back to legacy approach"
                    )
                    return await func(*args, **kwargs)
                else:
                    raise

        return wrapper

    return decorator


def lazy_load_aware(
    content_targets: List[ContentTarget],
    max_wait_time: int = 30,
) -> Callable[[F], F]:
    """Decorator to ensure specific content is loaded before function execution.

    This decorator focuses specifically on intelligent content loading,
    without full stealth control. Useful for functions that only need
    content loading without navigation or interaction simulation.

    Args:
        content_targets: List of content sections to ensure are loaded
        max_wait_time: Maximum time to wait for content loading

    Example:
        @lazy_load_aware([ContentTarget.EXPERIENCE, ContentTarget.EDUCATION])
        async def extract_work_history(page: Page) -> List[Experience]:
            # Experience and education sections guaranteed to be loaded
            return extract_experiences(page)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract page from arguments
            page = None
            for arg in args:
                if isinstance(arg, Page):
                    page = arg
                    break

            if page is None:
                page = kwargs.get("page")

            if page is None:
                logger.warning("No Page instance found, skipping lazy load")
                return await func(*args, **kwargs)

            # Import here to avoid circular imports
            from linkedin_mcp_server.scraper.stealth.lazy_loading import (
                LazyLoadDetector,
            )
            from linkedin_mcp_server.scraper.stealth.profiles import get_stealth_profile

            detector = LazyLoadDetector()
            profile = get_stealth_profile()

            try:
                # Ensure content is loaded
                result = await detector.ensure_content_loaded(
                    page=page,
                    targets=content_targets,
                    profile=profile,
                    max_wait_time=max_wait_time,
                )

                if not result.success:
                    logger.warning(
                        f"Failed to load some content: {result.missing_targets}"
                    )

                # Call original function
                return await func(*args, **kwargs)

            except Exception as e:
                logger.warning(f"Lazy loading failed ({e}), proceeding anyway")
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def performance_monitored(
    operation_name: str,
    page_type: str = "profile",
) -> Callable[[F], F]:
    """Decorator to monitor performance of scraping operations.

    This decorator automatically records timing and success/failure metrics
    for telemetry and optimization purposes.

    Args:
        operation_name: Name of the operation for telemetry
        page_type: Type of page being scraped

    Example:
        @performance_monitored("profile_extraction", "profile")
        async def extract_profile_sections(page: Page, url: str) -> Person:
            return extract_data(page)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import time

            # Extract url from arguments
            url = None
            for arg in args:
                if isinstance(arg, str) and (
                    "linkedin.com" in arg or arg.startswith("http")
                ):
                    url = arg
                    break

            if url is None:
                url = kwargs.get("url") or kwargs.get("linkedin_url") or "unknown"

            # Import here to avoid circular imports
            from linkedin_mcp_server.scraper.stealth.telemetry import (
                PerformanceTelemetry,
            )
            from linkedin_mcp_server.scraper.stealth.profiles import get_stealth_profile

            telemetry = PerformanceTelemetry()
            profile = get_stealth_profile()

            start_time = time.time()

            try:
                # Call original function
                result = await func(*args, **kwargs)

                # Record success
                duration = time.time() - start_time
                await telemetry.record_success(
                    url=url,
                    duration=duration,
                    profile_name=profile.name,
                    page_type=page_type,
                )

                return result

            except Exception as e:
                # Record failure
                duration = time.time() - start_time
                await telemetry.record_failure(
                    url=url,
                    duration=duration,
                    error=str(e),
                    profile_name=profile.name,
                    page_type=page_type,
                )
                raise

        return wrapper

    return decorator


def stealth_retry(
    max_retries: int = 2,
    backoff_multiplier: float = 1.5,
    escalate_stealth: bool = True,
) -> Callable[[F], F]:
    """Decorator to retry operations with escalating stealth levels on failure.

    This decorator automatically retries failed operations, optionally
    escalating to higher stealth levels on each retry.

    Args:
        max_retries: Maximum number of retries
        backoff_multiplier: Delay multiplier between retries
        escalate_stealth: Whether to increase stealth level on retries

    Example:
        @stealth_retry(max_retries=2, escalate_stealth=True)
        async def scrape_sensitive_content(page: Page, url: str) -> Data:
            return extract_data(page)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            import os

            from linkedin_mcp_server.scraper.config import LinkedInDetectionError

            original_profile = os.getenv("STEALTH_PROFILE", "MINIMAL_STEALTH")
            stealth_levels = ["MINIMAL_STEALTH", "MODERATE_STEALTH", "MAXIMUM_STEALTH"]

            for attempt in range(max_retries + 1):
                try:
                    # Set stealth level for this attempt
                    if escalate_stealth and attempt > 0:
                        level_index = min(attempt, len(stealth_levels) - 1)
                        os.environ["STEALTH_PROFILE"] = stealth_levels[level_index]
                        logger.info(
                            f"Retry {attempt}: Escalating to {stealth_levels[level_index]}"
                        )

                    # Call original function
                    result = await func(*args, **kwargs)

                    # Success - restore original profile
                    os.environ["STEALTH_PROFILE"] = original_profile
                    return result

                except LinkedInDetectionError as e:
                    if attempt < max_retries:
                        # Wait before retry with backoff
                        delay = backoff_multiplier**attempt
                        logger.warning(
                            f"Detection error on attempt {attempt + 1}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Restore original profile and re-raise
                        os.environ["STEALTH_PROFILE"] = original_profile
                        raise

                except Exception as e:
                    if attempt < max_retries:
                        delay = backoff_multiplier**attempt
                        logger.warning(
                            f"Error on attempt {attempt + 1}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Restore original profile and re-raise
                        os.environ["STEALTH_PROFILE"] = original_profile
                        raise

            # This should never be reached
            os.environ["STEALTH_PROFILE"] = original_profile
            raise Exception("Max retries exceeded")

        return wrapper

    return decorator


# Convenience decorators for common patterns


def profile_scraping_stealth(func: F) -> F:
    """Convenience decorator for profile scraping with full stealth control."""
    return stealth_controlled(
        page_type=PageType.PROFILE,
        content_targets=[
            ContentTarget.BASIC_INFO,
            ContentTarget.EXPERIENCE,
            ContentTarget.EDUCATION,
            ContentTarget.SKILLS,
            ContentTarget.ACCOMPLISHMENTS,
            ContentTarget.CONTACTS,
        ],
    )(func)


def job_scraping_stealth(func: F) -> F:
    """Convenience decorator for job scraping with stealth control."""
    return stealth_controlled(
        page_type=PageType.JOB_LISTING,
        content_targets=[
            ContentTarget.JOB_DESCRIPTION,
            ContentTarget.COMPANY_INFO,
        ],
    )(func)


def company_scraping_stealth(func: F) -> F:
    """Convenience decorator for company scraping with stealth control."""
    return stealth_controlled(
        page_type=PageType.COMPANY_PAGE,
        content_targets=[
            ContentTarget.COMPANY_OVERVIEW,
            ContentTarget.EMPLOYEES,
        ],
    )(func)


# Example usage patterns (commented out - for documentation)
"""
# Full stealth control for profile scraping
@profile_scraping_stealth
async def scrape_complete_profile(page: Page, url: str) -> Person:
    return extract_profile_data(page)

# Just content loading for specific sections
@lazy_load_aware([ContentTarget.EXPERIENCE, ContentTarget.EDUCATION])
async def extract_work_education(page: Page) -> Tuple[List[Experience], List[Education]]:
    return extract_experiences(page), extract_education(page)

# Performance monitoring
@performance_monitored("profile_basic_info", "profile")
async def extract_basic_info(page: Page, url: str) -> BasicInfo:
    return extract_basic_info_data(page)

# Retry with stealth escalation
@stealth_retry(max_retries=2, escalate_stealth=True)
async def scrape_protected_content(page: Page, url: str) -> Data:
    return extract_sensitive_data(page)

# Combination of decorators
@stealth_retry(max_retries=1)
@performance_monitored("profile_extraction")
@profile_scraping_stealth
async def robust_profile_scraping(page: Page, url: str) -> Person:
    return extract_complete_profile(page)
"""
