"""Proven LinkedIn CSS selectors and performance benchmarking utilities.

This module provides reliable CSS selectors adapted from working selenium implementations
and performance tracking utilities for profile section extraction.
"""

import logging
import time


class LinkedInSelectors:
    """Reliable CSS selectors adapted from working selenium implementation.
    
    These selectors are based on proven patterns from legacy implementations that
    successfully generated the testscrape.txt baseline data.
    """

    # Main profile sections
    EXPERIENCE_SECTION = "section:has(#experience)"
    EDUCATION_SECTION = "section:has(#education)"
    
    # Alternative section selectors for fallback
    EXPERIENCE_SECTION_ALT = [
        "section[data-view-name='profile-experience']",
        "section:has-text('Experience')",
        "main section:has-text('Experience')"
    ]
    
    EDUCATION_SECTION_ALT = [
        "section[data-view-name='profile-education']", 
        "section:has-text('Education')",
        "main section:has-text('Education')"
    ]

    # Core item selectors (proven from legacy selenium)
    EXPERIENCE_ITEMS = "div[data-view-name='profile-component-entity']"
    EDUCATION_ITEMS = "div[data-view-name='profile-component-entity']"
    
    # Alternative item selectors for fallback
    EXPERIENCE_ITEMS_ALT = [
        "ul.pvs-list li",
        ".pvs-entity",
        ".pvs-list__paged-list-item"
    ]
    
    EDUCATION_ITEMS_ALT = [
        "ul.pvs-list li", 
        ".pvs-entity",
        ".pvs-list__paged-list-item"
    ]

    # Clean text extraction selectors
    CLEAN_TEXT = "span[aria-hidden='true']"
    POSITION_TITLE = "h3 span[aria-hidden='true']"
    COMPANY_NAME = ".mr1.hoverable-link-text span[aria-hidden='true']"
    
    # Basic info selectors (adapted from working patterns)
    PROFILE_NAME = "h1"
    PROFILE_HEADLINE = [
        "h1 + div span[aria-hidden='true']",
        "h1 ~ div:first-of-type span[aria-hidden='true']",
        ".pv-text-details__left-panel > div:nth-child(2) span[aria-hidden='true']"
    ]
    
    PROFILE_LOCATION = [
        ".text-body-small.inline.t-black--light.break-words",
        ".pv-text-details__left-panel .text-body-small"
    ]
    
    PROFILE_ABOUT = [
        "#about ~ .display-flex",
        "#about + * .display-flex",
        "section:has(#about) .display-flex"
    ]


class PerformanceBenchmark:
    """Performance timing utilities for profile section extraction.
    
    Provides logging and timing metrics to track extraction performance
    and identify optimization opportunities.
    """

    @staticmethod
    def log_section_timing(
        section_name: str, 
        start_time: float, 
        end_time: float, 
        item_count: int,
        logger: logging.Logger
    ) -> None:
        """Log timing metrics for each profile section.
        
        Args:
            section_name: Name of the section being timed
            start_time: Start timestamp
            end_time: End timestamp  
            item_count: Number of items extracted
            logger: Logger instance to use
        """
        duration = end_time - start_time
        avg_per_item = duration / item_count if item_count > 0 else duration
        logger.info(
            f"BENCHMARK - {section_name}: {duration:.2f}s total, "
            f"{item_count} items, {avg_per_item:.3f}s/item"
        )

    @staticmethod
    def time_section(section_name: str, logger: logging.Logger):
        """Context manager for timing section extraction.
        
        Usage:
            with PerformanceBenchmark.time_section("experience", logger) as timer:
                # extraction logic
                timer.set_item_count(8)
        """
        return SectionTimer(section_name, logger)


class SectionTimer:
    """Context manager for timing profile section extraction."""
    
    def __init__(self, section_name: str, logger: logging.Logger):
        self.section_name = section_name
        self.logger = logger
        self.start_time = 0.0
        self.item_count = 0
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        PerformanceBenchmark.log_section_timing(
            self.section_name, 
            self.start_time, 
            end_time, 
            self.item_count,
            self.logger
        )
        
    def set_item_count(self, count: int) -> None:
        """Set the number of items extracted for performance calculation."""
        self.item_count = count


class LinkedInScrapingError(Exception):
    """Exception raised when LinkedIn scraping fails due to selector issues.
    
    This indicates that LinkedIn's DOM structure may have changed and 
    selectors need to be updated.
    """
    pass