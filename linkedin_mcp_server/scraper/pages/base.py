"""Abstract base class for LinkedIn page scrapers using centralized stealth."""

import logging
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from patchright.async_api import Page

from linkedin_mcp_server.scraper.stealth.controller import (
    ContentTarget,
    PageType,
    StealthController,
)

logger = logging.getLogger(__name__)


class LinkedInPageScraper(ABC):
    """Abstract base class for LinkedIn page scrapers.
    
    This class provides common functionality for all LinkedIn page types,
    using the centralized stealth architecture for optimal performance
    and maintainability.
    """
    
    def __init__(
        self,
        stealth_controller: Optional[StealthController] = None,
    ):
        """Initialize the page scraper.
        
        Args:
            stealth_controller: Optional stealth controller instance.
                                If None, creates one from configuration.
        """
        self.stealth_controller = stealth_controller or StealthController.from_config()
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    def get_page_type(self) -> PageType:
        """Get the page type for this scraper."""
        pass
    
    @abstractmethod
    def get_content_targets(self, **kwargs) -> List[ContentTarget]:
        """Get the content targets to load for this page type.
        
        Args:
            **kwargs: Page-specific parameters that may affect content targets
            
        Returns:
            List of ContentTarget enums for content that should be loaded
        """
        pass
    
    @abstractmethod
    async def extract_data(self, page: Page, **kwargs) -> Any:
        """Extract data from the loaded page.
        
        This method is called after stealth operations are complete
        and all content is loaded. It should focus purely on data
        extraction without any stealth considerations.
        
        Args:
            page: Patchright page instance with content loaded
            **kwargs: Page-specific extraction parameters
            
        Returns:
            Extracted data in the appropriate format
        """
        pass
    
    async def scrape_page(
        self,
        page: Page,
        url: str,
        **kwargs
    ) -> Any:
        """Main entry point for scraping a LinkedIn page.
        
        This method orchestrates the complete scraping process:
        1. Centralized stealth operations (navigation, loading, simulation)
        2. Data extraction (delegated to extract_data)
        
        Args:
            page: Patchright page instance
            url: LinkedIn URL to scrape
            **kwargs: Page-specific parameters
            
        Returns:
            Extracted data from the page
        """
        logger.info(f"Starting {self.get_page_type().value} scrape: {url}")
        
        # Phase 1: Centralized stealth operations
        content_targets = self.get_content_targets(**kwargs)
        
        scraping_result = await self.stealth_controller.scrape_linkedin_page(
            page=page,
            url=url,
            page_type=self.get_page_type(),
            content_targets=content_targets,
        )
        
        if not scraping_result.success:
            raise Exception(
                f"Stealth operations failed: {scraping_result.error}"
            )
        
        # Phase 2: Data extraction (pure extraction, no stealth)
        logger.debug("Stealth operations complete, extracting data")
        extracted_data = await self.extract_data(page, **kwargs)
        
        logger.info(
            f"Successfully scraped {self.get_page_type().value} "
            f"in {scraping_result.duration:.1f}s using {scraping_result.profile_used}"
        )
        
        return extracted_data
    
    async def prepare_page_for_extraction(
        self,
        page: Page,
        url: str,
        **kwargs
    ) -> None:
        """Prepare the page for data extraction without full scraping.
        
        This is a lighter-weight operation that only performs navigation
        and content loading without full interaction simulation.
        Useful for cases where you want to manually control extraction timing.
        
        Args:
            page: Patchright page instance
            url: LinkedIn URL to prepare
            **kwargs: Page-specific parameters
        """
        logger.debug(f"Preparing {self.get_page_type().value} page: {url}")
        
        # Navigate to page
        await self.stealth_controller.navigate_and_prepare_page(
            page, url, self.get_page_type()
        )
        
        # Ensure content is loaded
        content_targets = self.get_content_targets(**kwargs)
        loaded_targets = await self.stealth_controller.ensure_all_content_loaded(
            page, content_targets
        )
        
        logger.debug(
            f"Page prepared with {len(loaded_targets)} content targets loaded"
        )
    
    def _log_extraction_progress(self, section: str, success: bool = True) -> None:
        """Helper method to log extraction progress."""
        status = "✓" if success else "✗"
        logger.debug(f"{status} Extracted {section}")
    
    def _handle_extraction_error(
        self,
        section: str,
        error: Exception,
        return_none: bool = True
    ) -> Optional[Any]:
        """Helper method to handle extraction errors consistently.
        
        Args:
            section: Name of the section being extracted
            error: Exception that occurred
            return_none: Whether to return None or re-raise the error
            
        Returns:
            None if return_none is True, otherwise raises the error
        """
        logger.warning(f"Failed to extract {section}: {error}")
        
        if return_none:
            return None
        else:
            raise error