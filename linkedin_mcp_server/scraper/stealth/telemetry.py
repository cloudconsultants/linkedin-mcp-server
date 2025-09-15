"""Performance telemetry and monitoring for stealth operations."""

import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Metrics for a single operation."""

    timestamp: float
    url: str
    profile_name: str
    duration: float
    success: bool
    page_type: str
    error: Optional[str] = None


@dataclass
class AggregateMetrics:
    """Aggregated performance metrics."""

    profile_name: str
    total_operations: int
    success_rate: float
    avg_duration: float
    median_duration: float
    p95_duration: float
    min_duration: float
    max_duration: float
    operations_per_minute: float
    last_updated: float


class PerformanceTelemetry:
    """Performance telemetry system for monitoring stealth operations.

    This class collects and analyzes performance data to provide insights
    for optimizing stealth profiles and monitoring system health.
    """

    def __init__(
        self,
        max_history: int = 1000,
        persist_metrics: bool = True,
        metrics_file: Optional[str] = None,
    ):
        """Initialize performance telemetry.

        Args:
            max_history: Maximum number of metrics to keep in memory
            persist_metrics: Whether to persist metrics to disk
            metrics_file: Path to metrics file (defaults to temp directory)
        """
        self.max_history = max_history
        self.persist_metrics = persist_metrics

        # In-memory storage
        self.metrics_history: deque = deque(maxlen=max_history)
        self.profile_stats: Dict[str, List[PerformanceMetrics]] = defaultdict(list)

        # File persistence
        if metrics_file:
            self.metrics_file = Path(metrics_file)
        else:
            self.metrics_file = Path("/tmp/linkedin_mcp_telemetry.json")

        # Load existing metrics if available
        if persist_metrics and self.metrics_file.exists():
            self._load_metrics()

        logger.info(f"PerformanceTelemetry initialized with file: {self.metrics_file}")

    async def record_success(
        self,
        url: str,
        duration: float,
        profile_name: str,
        page_type: str = "profile",
    ) -> None:
        """Record a successful operation.

        Args:
            url: LinkedIn URL that was scraped
            duration: Operation duration in seconds
            profile_name: Stealth profile used
            page_type: Type of page scraped
        """
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            url=url,
            profile_name=profile_name,
            duration=duration,
            success=True,
            page_type=page_type,
        )

        await self._record_metrics(metrics)

        logger.debug(
            f"Recorded success: {profile_name} - {duration:.1f}s on {page_type}"
        )

    async def record_failure(
        self,
        url: str,
        duration: float,
        error: str,
        profile_name: str = "unknown",
        page_type: str = "profile",
    ) -> None:
        """Record a failed operation.

        Args:
            url: LinkedIn URL that was attempted
            duration: Operation duration before failure
            error: Error message
            profile_name: Stealth profile used
            page_type: Type of page attempted
        """
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            url=url,
            profile_name=profile_name,
            duration=duration,
            success=False,
            page_type=page_type,
            error=error,
        )

        await self._record_metrics(metrics)

        logger.warning(f"Recorded failure: {profile_name} - {duration:.1f}s - {error}")

    def get_profile_stats(self, profile_name: str) -> Optional[AggregateMetrics]:
        """Get aggregate statistics for a specific profile.

        Args:
            profile_name: Name of the stealth profile

        Returns:
            AggregateMetrics if data available, None otherwise
        """
        if profile_name not in self.profile_stats:
            return None

        metrics_list = self.profile_stats[profile_name]
        if not metrics_list:
            return None

        # Calculate statistics
        durations = [m.duration for m in metrics_list]
        successes = [m for m in metrics_list if m.success]

        # Time-based calculations
        if len(metrics_list) > 1:
            time_span = metrics_list[-1].timestamp - metrics_list[0].timestamp
            ops_per_minute = (
                len(metrics_list) / (time_span / 60) if time_span > 0 else 0
            )
        else:
            ops_per_minute = 0

        return AggregateMetrics(
            profile_name=profile_name,
            total_operations=len(metrics_list),
            success_rate=len(successes) / len(metrics_list),
            avg_duration=statistics.mean(durations),
            median_duration=statistics.median(durations),
            p95_duration=statistics.quantiles(durations, n=20)[18]
            if len(durations) >= 20
            else max(durations),
            min_duration=min(durations),
            max_duration=max(durations),
            operations_per_minute=ops_per_minute,
            last_updated=time.time(),
        )

    def get_all_stats(self) -> Dict[str, AggregateMetrics]:
        """Get aggregate statistics for all profiles."""
        stats = {}
        for profile_name in self.profile_stats.keys():
            profile_stats = self.get_profile_stats(profile_name)
            if profile_stats:
                stats[profile_name] = profile_stats
        return stats

    def get_performance_comparison(self) -> Dict[str, Dict[str, float]]:
        """Get performance comparison between profiles.

        Returns:
            Dictionary with profile comparisons and improvements
        """
        all_stats = self.get_all_stats()
        if len(all_stats) < 2:
            return {}

        # Use MAXIMUM_STEALTH as baseline if available
        baseline_profile = None
        if "MAXIMUM_STEALTH" in all_stats:
            baseline_profile = "MAXIMUM_STEALTH"
            baseline_duration = all_stats["MAXIMUM_STEALTH"].avg_duration
        else:
            # Use slowest profile as baseline
            slowest = max(all_stats.values(), key=lambda x: x.avg_duration)
            baseline_profile = slowest.profile_name
            baseline_duration = slowest.avg_duration

        comparisons = {}
        for profile_name, stats in all_stats.items():
            if profile_name == baseline_profile:
                comparisons[profile_name] = {
                    "avg_duration": stats.avg_duration,
                    "improvement_pct": 0.0,
                    "speed_multiplier": 1.0,
                }
            else:
                improvement_pct = (
                    (baseline_duration - stats.avg_duration) / baseline_duration * 100
                )
                speed_multiplier = baseline_duration / stats.avg_duration

                comparisons[profile_name] = {
                    "avg_duration": stats.avg_duration,
                    "improvement_pct": improvement_pct,
                    "speed_multiplier": speed_multiplier,
                }

        return comparisons

    def get_optimization_suggestions(self) -> List[str]:
        """Get optimization suggestions based on performance data."""
        suggestions = []
        all_stats = self.get_all_stats()

        if not all_stats:
            return ["No performance data available yet."]

        # Check success rates
        for profile_name, stats in all_stats.items():
            if stats.success_rate < 0.9:
                suggestions.append(
                    f"{profile_name}: Low success rate ({stats.success_rate:.1%}). "
                    "Consider increasing delays or switching to higher stealth level."
                )

        # Check performance targets
        comparisons = self.get_performance_comparison()
        for profile_name, comp in comparisons.items():
            if profile_name == "NO_STEALTH" and comp["avg_duration"] > 60:
                suggestions.append(
                    f"NO_STEALTH taking {comp['avg_duration']:.1f}s "
                    "(target: <50s). Check for bottlenecks."
                )
            elif profile_name == "MINIMAL_STEALTH" and comp["avg_duration"] > 90:
                suggestions.append(
                    f"MINIMAL_STEALTH taking {comp['avg_duration']:.1f}s "
                    "(target: <75s). Consider optimization."
                )

        # Check for detection patterns
        recent_failures = [
            m
            for m in list(self.metrics_history)[-50:]  # Last 50 operations
            if not m.success and "challenge" in (m.error or "").lower()
        ]

        if len(recent_failures) > 5:
            suggestions.append(
                f"Detected {len(recent_failures)} challenges in recent operations. "
                "Consider increasing stealth level or reducing request rate."
            )

        if not suggestions:
            suggestions.append("Performance looks good! No optimization needed.")

        return suggestions

    def print_performance_report(self) -> str:
        """Generate a formatted performance report."""
        all_stats = self.get_all_stats()
        if not all_stats:
            return "No performance data available."

        report = []
        report.append("=== LinkedIn MCP Performance Report ===\n")

        # Profile statistics
        for profile_name, stats in sorted(all_stats.items()):
            report.append(f"Profile: {profile_name}")
            report.append(f"  Operations: {stats.total_operations}")
            report.append(f"  Success Rate: {stats.success_rate:.1%}")
            report.append(f"  Avg Duration: {stats.avg_duration:.1f}s")
            report.append(f"  Median Duration: {stats.median_duration:.1f}s")
            report.append(f"  95th Percentile: {stats.p95_duration:.1f}s")
            report.append(
                f"  Range: {stats.min_duration:.1f}s - {stats.max_duration:.1f}s"
            )
            if stats.operations_per_minute > 0:
                report.append(f"  Ops/min: {stats.operations_per_minute:.1f}")
            report.append("")

        # Performance comparisons
        comparisons = self.get_performance_comparison()
        if comparisons:
            report.append("=== Performance Improvements ===")
            for profile_name, comp in sorted(comparisons.items()):
                if comp["improvement_pct"] > 0:
                    report.append(
                        f"{profile_name}: {comp['improvement_pct']:.1f}% faster "
                        f"({comp['avg_duration']:.1f}s avg)"
                    )
                else:
                    report.append(
                        f"{profile_name}: {comp['avg_duration']:.1f}s avg (baseline)"
                    )
            report.append("")

        # Optimization suggestions
        suggestions = self.get_optimization_suggestions()
        if suggestions:
            report.append("=== Optimization Suggestions ===")
            for suggestion in suggestions:
                report.append(f"• {suggestion}")

        return "\n".join(report)

    async def _record_metrics(self, metrics: PerformanceMetrics) -> None:
        """Record metrics to memory and optionally persist."""
        # Add to memory
        self.metrics_history.append(metrics)
        self.profile_stats[metrics.profile_name].append(metrics)

        # Trim profile-specific stats if needed
        if len(self.profile_stats[metrics.profile_name]) > self.max_history:
            self.profile_stats[metrics.profile_name] = self.profile_stats[
                metrics.profile_name
            ][-self.max_history :]

        # Persist to disk
        if self.persist_metrics:
            await self._persist_metrics()

    async def _persist_metrics(self) -> None:
        """Persist metrics to disk."""
        try:
            # Convert to serializable format
            data = {
                "metrics_history": [asdict(m) for m in list(self.metrics_history)],
                "last_updated": time.time(),
            }

            # Write atomically
            temp_file = self.metrics_file.with_suffix(".tmp")
            with temp_file.open("w") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.metrics_file)

        except Exception as e:
            logger.warning(f"Failed to persist metrics: {e}")

    def _load_metrics(self) -> None:
        """Load metrics from disk."""
        try:
            with self.metrics_file.open("r") as f:
                data = json.load(f)

            # Restore metrics
            for metrics_dict in data.get("metrics_history", []):
                # Ensure all required fields are present with defaults
                required_fields = {
                    "timestamp": time.time(),
                    "url": "",
                    "profile_name": "unknown", 
                    "duration": 0.0,
                    "success": True,
                    "page_type": "profile",
                    "error": None
                }
                
                # Update with actual data
                for key, value in metrics_dict.items():
                    if key in required_fields:
                        required_fields[key] = value
                
                metrics = PerformanceMetrics(**required_fields)
                self.metrics_history.append(metrics)
                self.profile_stats[metrics.profile_name].append(metrics)

            logger.info(f"Loaded {len(self.metrics_history)} historical metrics")

        except Exception as e:
            logger.warning(f"Failed to load metrics: {e}")

    def clear_metrics(self) -> None:
        """Clear all metrics data."""
        self.metrics_history.clear()
        self.profile_stats.clear()

        if self.persist_metrics and self.metrics_file.exists():
            try:
                self.metrics_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete metrics file: {e}")

        logger.info("All metrics data cleared")
