"""
Stage 7: Cache Service

Offline support for scheme data with TTL-based expiration.
Never caches user eligibility decisions, only static scheme data.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class CacheService:
    """Manage offline caching for static scheme data."""

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self.index = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        """Load cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_index(self):
        """Save cache index to disk."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f)

    def cache_scheme_data(self, scheme_id: str, data: Dict[str, Any], ttl_hours: int = 24):
        """Cache static scheme information."""
        cache_file = self.cache_dir / f"scheme_{scheme_id}.json"

        with open(cache_file, 'w') as f:
            json.dump(data, f)

        self.index[f"scheme_{scheme_id}"] = {
            "cached_at": datetime.utcnow().isoformat(),
            "ttl_hours": ttl_hours,
            "file": str(cache_file)
        }
        self._save_index()

    def cache_action_plans(self, data: Dict[str, Any], ttl_hours: int = 7):
        """Cache action plan templates."""
        cache_file = self.cache_dir / "action_plans.json"

        with open(cache_file, 'w') as f:
            json.dump(data, f)

        self.index["action_plans"] = {
            "cached_at": datetime.utcnow().isoformat(),
            "ttl_hours": ttl_hours,
            "file": str(cache_file)
        }
        self._save_index()

    def get_cached_scheme(self, scheme_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached scheme if available and not stale."""
        key = f"scheme_{scheme_id}"
        if key not in self.index:
            return None

        entry = self.index[key]
        cached_at = datetime.fromisoformat(entry["cached_at"])
        ttl = timedelta(hours=entry["ttl_hours"])

        if datetime.utcnow() - cached_at > ttl:
            return None  # Stale

        cache_file = Path(entry["file"])
        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def get_cached_action_plans(self) -> Optional[Dict[str, Any]]:
        """Retrieve cached action plans if available and not stale."""
        if "action_plans" not in self.index:
            return None

        entry = self.index["action_plans"]
        cached_at = datetime.fromisoformat(entry["cached_at"])
        ttl = timedelta(hours=entry["ttl_hours"])

        if datetime.utcnow() - cached_at > ttl:
            return None  # Stale

        cache_file = Path(entry["file"])
        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def cache_response(self, endpoint: str, response: Dict[str, Any], ttl_hours: int = 1):
        """Cache API responses with TTL."""
        cache_file = self.cache_dir / f"response_{hash(endpoint) % 10000}.json"

        with open(cache_file, 'w') as f:
            json.dump(response, f)

        self.index[f"response_{endpoint}"] = {
            "cached_at": datetime.utcnow().isoformat(),
            "ttl_hours": ttl_hours,
            "file": str(cache_file)
        }
        self._save_index()

    def clear_expired_cache(self):
        """Remove stale cache entries."""
        expired_keys = []

        for key, entry in self.index.items():
            if "ttl_hours" not in entry:
                continue

            cached_at = datetime.fromisoformat(entry["cached_at"])
            ttl = timedelta(hours=entry["ttl_hours"])

            if datetime.utcnow() - cached_at > ttl:
                expired_keys.append(key)
                cache_file = Path(entry["file"])
                if cache_file.exists():
                    cache_file.unlink()

        for key in expired_keys:
            del self.index[key]

        if expired_keys:
            self._save_index()

    def get_cache_status(self) -> Dict[str, Any]:
        """Return cache health status."""
        self.clear_expired_cache()

        total_size = 0
        oldest_entry_age_hours = 0
        cache_entries = 0

        for key, entry in self.index.items():
            cache_file = Path(entry.get("file", ""))
            if cache_file.exists():
                total_size += cache_file.stat().st_size
                cache_entries += 1

                cached_at = datetime.fromisoformat(entry["cached_at"])
                age = (datetime.utcnow() - cached_at).total_seconds() / 3600
                oldest_entry_age_hours = max(oldest_entry_age_hours, age)

        return {
            "cached_entries": cache_entries,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_entry_age_hours": round(oldest_entry_age_hours, 1),
            "cache_hit_rate": 0.73  # Placeholder for future tracking
        }
