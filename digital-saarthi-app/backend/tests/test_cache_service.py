"""
Stage 7 Tests: Cache Service
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from app.cache_service import CacheService


class TestCacheServiceSchemeData:
    """Test scheme data caching."""

    def test_cache_scheme_data(self):
        """Cache scheme data with TTL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheService(tmpdir)
            scheme_data = {
                "name": "IGNOAPS",
                "eligibility": "Age >= 60 AND BPL"
            }

            cache.cache_scheme_data("ignoaps", scheme_data, ttl_hours=24)

            # Verify cached
            cached = cache.get_cached_scheme("ignoaps")
            assert cached is not None
            assert cached["name"] == "IGNOAPS"

    def test_cache_expiration(self):
        """Cached data expires after TTL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheService(tmpdir)
            scheme_data = {"name": "IGNOAPS"}

            cache.cache_scheme_data("ignoaps", scheme_data, ttl_hours=0)

            # Immediately expired
            import time
            time.sleep(0.1)
            cached = cache.get_cached_scheme("ignoaps")
            assert cached is None

    def test_cache_missing_scheme(self):
        """Requesting uncached scheme returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheService(tmpdir)
            cached = cache.get_cached_scheme("nonexistent")
            assert cached is None


class TestCacheServiceActionPlans:
    """Test action plan caching."""

    def test_cache_action_plans(self):
        """Cache action plan templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheService(tmpdir)
            plans = {
                "ignoaps": ["Step 1: Visit office", "Step 2: Submit docs"]
            }

            cache.cache_action_plans(plans, ttl_hours=7)

            cached = cache.get_cached_action_plans()
            assert cached is not None
            assert "ignoaps" in cached

    def test_cache_action_plans_expiration(self):
        """Action plans expire after TTL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheService(tmpdir)
            plans = {"ignoaps": ["Step 1"]}

            cache.cache_action_plans(plans, ttl_hours=0)

            import time
            time.sleep(0.1)
            cached = cache.get_cached_action_plans()
            assert cached is None


class TestCacheServiceResponses:
    """Test API response caching."""

    def test_cache_response(self):
        """Cache API responses with TTL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheService(tmpdir)
            response = {"eligible": True, "reason": "Test"}

            cache.cache_response("/check_eligibility", response, ttl_hours=1)

            status = cache.get_cache_status()
            assert status["cached_entries"] > 0

    def test_clear_expired_cache(self):
        """Clear expired cache entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheService(tmpdir)

            # Add expired entry
            cache.cache_scheme_data("test", {"data": "test"}, ttl_hours=0)

            import time
            time.sleep(0.1)

            cache.clear_expired_cache()

            status = cache.get_cache_status()
            # Entry should be cleaned up (or minimal)
            assert status["cached_entries"] == 0


class TestCacheStatus:
    """Test cache status reporting."""

    def test_cache_status_empty(self):
        """Cache status for empty cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheService(tmpdir)
            status = cache.get_cache_status()

            assert status["cached_entries"] == 0
            assert status["total_size_mb"] == 0

    def test_cache_status_with_data(self):
        """Cache status includes populated cache metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheService(tmpdir)
            cache.cache_scheme_data("ignoaps", {"name": "IGNOAPS"}, ttl_hours=24)

            status = cache.get_cache_status()
            assert status["cached_entries"] > 0
            assert "total_size_mb" in status
            assert "oldest_entry_age_hours" in status
