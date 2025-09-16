#!/usr/bin/env python3
"""Performance benchmark script for stealth system comparison.

This script compares the performance of different stealth profiles
to validate the speed improvements claimed in the PRP.

Usage:
    python benchmark_stealth_performance.py --profiles NO_STEALTH,MINIMAL_STEALTH,MAXIMUM_STEALTH \\
        --urls linkedin.com/in/testuser1,linkedin.com/in/testuser2 \\
        --iterations 3
"""

import argparse
import asyncio
import json
import os
import statistics
import time
from typing import Dict, List
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def benchmark_stealth_profile(
    profile_name: str,
    test_urls: List[str],
    iterations: int = 3,
) -> Dict[str, float]:
    """Benchmark a specific stealth profile.

    Args:
        profile_name: Name of stealth profile to test
        test_urls: List of LinkedIn URLs to test against
        iterations: Number of iterations per URL

    Returns:
        Dictionary with performance metrics
    """
    try:
        from linkedin_mcp_server.scraper.stealth.controller import (
            StealthController,
            PageType,
            ContentTarget,
        )
        from linkedin_mcp_server.scraper.stealth.profiles import get_stealth_profile
        from unittest.mock import AsyncMock

        # Get profile
        profile = get_stealth_profile(profile_name)
        controller = StealthController(profile=profile, telemetry=False)

        durations = []
        success_count = 0
        total_operations = len(test_urls) * iterations

        logger.info(f"Benchmarking {profile_name}: {total_operations} operations")

        for url in test_urls:
            for i in range(iterations):
                try:
                    # Create mock page for testing
                    mock_page = AsyncMock()

                    # Set environment for this profile
                    original_profile = os.environ.get("STEALTH_PROFILE")
                    os.environ["STEALTH_PROFILE"] = profile_name

                    start_time = time.time()

                    # Simulate profile scraping
                    result = await controller.scrape_linkedin_page(
                        page=mock_page,
                        url=f"https://{url}",
                        page_type=PageType.PROFILE,
                        content_targets=[
                            ContentTarget.BASIC_INFO,
                            ContentTarget.EXPERIENCE,
                            ContentTarget.EDUCATION,
                        ],
                    )

                    duration = time.time() - start_time
                    durations.append(duration)

                    if result.success:
                        success_count += 1

                    logger.debug(
                        f"{profile_name} iteration {i + 1} for {url}: "
                        f"{duration:.1f}s ({'success' if result.success else 'failed'})"
                    )

                    # Restore original profile
                    if original_profile:
                        os.environ["STEALTH_PROFILE"] = original_profile
                    elif "STEALTH_PROFILE" in os.environ:
                        del os.environ["STEALTH_PROFILE"]

                    # Brief pause between iterations
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Benchmark error for {profile_name}: {e}")
                    durations.append(float("inf"))  # Mark as failed

        if not durations or not any(d != float("inf") for d in durations):
            return {
                "profile_name": profile_name,
                "avg_duration": float("inf"),
                "median_duration": float("inf"),
                "min_duration": float("inf"),
                "max_duration": float("inf"),
                "success_rate": 0.0,
                "total_operations": total_operations,
            }

        # Filter out failed operations for statistics
        successful_durations = [d for d in durations if d != float("inf")]

        return {
            "profile_name": profile_name,
            "avg_duration": statistics.mean(successful_durations),
            "median_duration": statistics.median(successful_durations),
            "min_duration": min(successful_durations),
            "max_duration": max(successful_durations),
            "success_rate": success_count / total_operations,
            "total_operations": total_operations,
            "successful_operations": len(successful_durations),
        }

    except Exception as e:
        logger.error(f"Failed to benchmark {profile_name}: {e}")
        return {
            "profile_name": profile_name,
            "avg_duration": float("inf"),
            "error": str(e),
        }


def calculate_performance_improvements(
    results: List[Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    """Calculate performance improvements relative to baseline.

    Args:
        results: List of benchmark results

    Returns:
        Dictionary with performance comparisons
    """
    # Find baseline (slowest successful profile, preferably MAXIMUM_STEALTH)
    successful_results = [r for r in results if r.get("success_rate", 0) > 0]
    if not successful_results:
        return {}

    # Use MAXIMUM_STEALTH as baseline if available, otherwise slowest
    baseline = None
    for result in successful_results:
        if result["profile_name"] == "MAXIMUM_STEALTH":
            baseline = result
            break

    if baseline is None:
        baseline = max(successful_results, key=lambda x: x["avg_duration"])

    baseline_duration = baseline["avg_duration"]

    improvements = {}
    for result in successful_results:
        profile_name = result["profile_name"]
        duration = result["avg_duration"]

        improvement_pct = ((baseline_duration - duration) / baseline_duration) * 100
        speed_multiplier = baseline_duration / duration

        improvements[profile_name] = {
            "avg_duration": duration,
            "improvement_pct": improvement_pct,
            "speed_multiplier": speed_multiplier,
            "success_rate": result["success_rate"],
        }

    return improvements


def print_benchmark_results(
    results: List[Dict[str, float]], improvements: Dict[str, Dict[str, float]]
) -> None:
    """Print formatted benchmark results."""
    print("\n" + "=" * 60)
    print("LinkedIn MCP Stealth System Performance Benchmark")
    print("=" * 60)

    # Individual profile results
    print("\n📊 Profile Performance Results:")
    print("-" * 60)

    for result in sorted(results, key=lambda x: x.get("avg_duration", float("inf"))):
        profile = result["profile_name"]
        if result.get("error"):
            print(f"❌ {profile}: ERROR - {result['error']}")
            continue

        duration = result["avg_duration"]
        success_rate = result.get("success_rate", 0)

        print(f"🔹 {profile}:")
        print(f"   Average: {duration:.1f}s")
        print(
            f"   Range: {result['min_duration']:.1f}s - {result['max_duration']:.1f}s"
        )
        print(f"   Success Rate: {success_rate:.1%}")
        print(
            f"   Operations: {result.get('successful_operations', 0)}/{result.get('total_operations', 0)}"
        )
        print()

    # Performance improvements
    if improvements:
        print("🚀 Performance Improvements:")
        print("-" * 60)

        for profile_name, improvement in sorted(
            improvements.items(), key=lambda x: x[1]["improvement_pct"], reverse=True
        ):
            duration = improvement["avg_duration"]
            improvement_pct = improvement["improvement_pct"]

            if improvement_pct > 0:
                print(
                    f"✅ {profile_name}: {improvement_pct:.1f}% faster ({duration:.1f}s avg)"
                )
            elif improvement_pct == 0:
                print(f"📌 {profile_name}: {duration:.1f}s avg (baseline)")
            else:
                print(
                    f"⚠️  {profile_name}: {abs(improvement_pct):.1f}% slower ({duration:.1f}s avg)"
                )

        print()

    # Performance targets validation
    print("🎯 Performance Target Validation:")
    print("-" * 60)

    targets = {
        "NO_STEALTH": 50.0,  # Target: <50s
        "MINIMAL_STEALTH": 75.0,  # Target: <75s
        "MODERATE_STEALTH": 150.0,  # Target: <150s
        "MAXIMUM_STEALTH": 300.0,  # Current baseline: ~300s
    }

    for profile_name, target in targets.items():
        result = next((r for r in results if r["profile_name"] == profile_name), None)
        if not result or result.get("error"):
            print(f"❓ {profile_name}: No data")
            continue

        duration = result["avg_duration"]
        if duration <= target:
            print(f"✅ {profile_name}: {duration:.1f}s (target: <{target}s)")
        else:
            print(
                f"❌ {profile_name}: {duration:.1f}s (target: <{target}s) - MISSED TARGET"
            )

    print("\n" + "=" * 60)


async def main():
    """Main benchmark execution."""
    parser = argparse.ArgumentParser(
        description="Benchmark LinkedIn MCP stealth system performance"
    )
    parser.add_argument(
        "--profiles",
        default="NO_STEALTH,MINIMAL_STEALTH,MODERATE_STEALTH,MAXIMUM_STEALTH",
        help="Comma-separated list of stealth profiles to test",
    )
    parser.add_argument(
        "--urls",
        default="linkedin.com/in/testuser1,linkedin.com/in/testuser2",
        help="Comma-separated list of LinkedIn URLs to test (without https://)",
    )
    parser.add_argument(
        "--iterations", type=int, default=3, help="Number of iterations per URL"
    )
    parser.add_argument("--output", help="JSON file to save results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    profiles = [p.strip() for p in args.profiles.split(",")]
    urls = [u.strip() for u in args.urls.split(",")]

    logger.info(
        f"Starting benchmark: {len(profiles)} profiles x {len(urls)} URLs x {args.iterations} iterations"
    )

    # Run benchmarks
    results = []
    for profile in profiles:
        logger.info(f"Benchmarking profile: {profile}")
        result = await benchmark_stealth_profile(profile, urls, args.iterations)
        results.append(result)

    # Calculate improvements
    improvements = calculate_performance_improvements(results)

    # Print results
    print_benchmark_results(results, improvements)

    # Save results if requested
    if args.output:
        output_data = {
            "benchmark_results": results,
            "performance_improvements": improvements,
            "benchmark_config": {
                "profiles": profiles,
                "urls": urls,
                "iterations": args.iterations,
            },
        }

        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)

        logger.info(f"Results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
