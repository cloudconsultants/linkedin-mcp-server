"""Advanced performance monitoring for aggressive optimization validation."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractionMetrics:
    """Detailed extraction performance metrics."""

    profile_name: str
    url: str
    total_duration: float
    navigation_time: float
    content_loading_time: float
    simulation_time: float
    extraction_time: float
    success: bool
    error: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PerformanceMonitor:
    """Monitor and validate aggressive performance optimizations."""

    def __init__(self):
        self.metrics: List[ExtractionMetrics] = []
        self.performance_targets = {
            "NO_STEALTH": 2.0,
            "MINIMAL_STEALTH": 10.0,
            "MAXIMUM_STEALTH": 30.0,
        }

    def record_extraction(self, metrics: ExtractionMetrics) -> None:
        """Record extraction performance metrics."""
        self.metrics.append(metrics)

        # Immediate performance validation
        target = self.performance_targets.get(metrics.profile_name)
        if target and metrics.success:
            if metrics.total_duration <= target:
                logger.info(
                    f"✅ {metrics.profile_name} achieved target: {metrics.total_duration:.2f}s <= {target}s"
                )
            else:
                logger.warning(
                    f"⚠️ {metrics.profile_name} missed target: {metrics.total_duration:.2f}s > {target}s"
                )

    def get_performance_summary(self, hours: int = 24) -> Dict:
        """Get performance summary for recent extractions."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff]

        summary = {}
        for profile in self.performance_targets.keys():
            profile_metrics = [
                m for m in recent_metrics if m.profile_name == profile and m.success
            ]

            if profile_metrics:
                durations = [m.total_duration for m in profile_metrics]
                summary[profile] = {
                    "count": len(profile_metrics),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "target": self.performance_targets[profile],
                    "success_rate": len(profile_metrics)
                    / len([m for m in recent_metrics if m.profile_name == profile]),
                }

        return summary
