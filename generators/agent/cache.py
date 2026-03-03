"""
Test Generation Cache

Caches generated test cases for performance optimization.
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib
import time

from generators.base import TestCase


@dataclass
class CacheEntry:
    """A cache entry"""
    test_cases: List[Dict]  # Serialized test cases
    created_at: float
    access_count: int = 0
    last_accessed: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "test_cases": self.test_cases,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'CacheEntry':
        return cls(**data)


class TestGenerationCache:
    """
    Test Generation Cache

    Caches generated test cases to improve performance.
    Uses LRU eviction policy.
    """

    def __init__(self, cache_dir: Optional[Path] = None,
                 max_entries: int = 1000,
                 enable_persistence: bool = True):
        """
        Initialize cache

        Args:
            cache_dir: Directory for persistent cache storage
            max_entries: Maximum number of cache entries
            enable_persistence: Whether to persist cache to disk
        """
        self.cache_dir = cache_dir or Path("test_generation_cache")
        self.max_entries = max_entries
        self.enable_persistence = enable_persistence

        self._memory_cache: Dict[str, CacheEntry] = {}

        if self.enable_persistence:
            self._load()

    def _make_key(self, operation: str, count: int,
                  strategy: str, config: Optional[Dict] = None) -> str:
        """
        Create cache key from parameters

        Args:
            operation: Operation name
            count: Number of tests requested
            strategy: Generation strategy
            config: Additional config

        Returns:
            Cache key
        """
        key_data = f"{operation}:{count}:{strategy}"

        if config:
            # Convert config to serializable format
            serializable_config = {}
            for k, v in config.items():
                if isinstance(v, Path):
                    serializable_config[k] = str(v)
                elif hasattr(v, '__dict__'):
                    serializable_config[k] = str(v)
                else:
                    serializable_config[k] = v

            # Sort config for consistent hashing
            config_str = json.dumps(serializable_config, sort_keys=True)
            key_data += f":{config_str}"

        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, operation: str, count: int,
            strategy: str, config: Optional[Dict] = None) -> Optional[List[TestCase]]:
        """
        Get cached test cases

        Args:
            operation: Operation name
            count: Number of tests
            strategy: Generation strategy
            config: Additional config

        Returns:
            List of test cases or None if not cached
        """
        key = self._make_key(operation, count, strategy, config)

        entry = self._memory_cache.get(key)
        if entry:
            # Update access stats
            entry.access_count += 1
            entry.last_accessed = time.time()

            # Deserialize test cases
            test_cases = [
                TestCase.from_dict(tc_data)
                for tc_data in entry.test_cases
            ]

            return test_cases[:count] if test_cases else None  # Return only requested count or None

        return None

    def put(self, operation: str, count: int, strategy: str,
            test_cases: List[TestCase],
            config: Optional[Dict] = None) -> None:
        """
        Cache test cases

        Args:
            operation: Operation name
            count: Number of tests
            strategy: Generation strategy
            test_cases: Test cases to cache
            config: Additional config
        """
        key = self._make_key(operation, count, strategy, config)

        # Check cache size and evict if necessary
        if len(self._memory_cache) >= self.max_entries:
            self._evict_lru()

        # Create entry
        now = time.time()
        entry = CacheEntry(
            test_cases=[tc.to_dict() for tc in test_cases],
            created_at=now,
            access_count=1,
            last_accessed=now,
        )

        self._memory_cache[key] = entry

        # Persist if enabled
        if self.enable_persistence:
            self._save()

    def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if not self._memory_cache:
            return

        # Find LRU entry
        lru_key = min(
            self._memory_cache.keys(),
            key=lambda k: self._memory_cache[k].last_accessed
        )

        del self._memory_cache[lru_key]

    def invalidate(self, operation: Optional[str] = None) -> None:
        """
        Invalidate cache entries

        Args:
            operation: Specific operation to invalidate, or None for all
        """
        if operation is None:
            # Clear all
            self._memory_cache.clear()
        else:
            # Since we can't easily match keys by operation without storing metadata,
            # we'll clear all cache entries when invalidating by operation.
            # A more sophisticated implementation would store operation in cache entry.
            self._memory_cache.clear()

        if self.enable_persistence:
            self._save()

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_accesses = sum(e.access_count for e in self._memory_cache.values())

        return {
            "size": len(self._memory_cache),
            "max_entries": self.max_entries,
            "total_accesses": total_accesses,
            "hit_rate": self._calculate_hit_rate(),
        }

    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate (simplified)"""
        # This is a simplified calculation
        # A real implementation would track hits and misses separately
        return 0.0

    def _save(self) -> None:
        """Save cache to disk"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            cache_data = {
                "version": "1.0",
                "entries": {
                    key: entry.to_dict()
                    for key, entry in self._memory_cache.items()
                }
            }

            cache_file = self.cache_dir / "cache.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            print(f"[WARNING] Failed to save cache: {e}")

    def _load(self) -> None:
        """Load cache from disk"""
        cache_file = self.cache_dir / "cache.json"

        if not cache_file.exists():
            return

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for key, entry_data in data.get("entries", {}).items():
                    self._memory_cache[key] = CacheEntry.from_dict(entry_data)

        except Exception as e:
            print(f"[WARNING] Failed to load cache: {e}")

    def clear(self) -> None:
        """Clear all cache entries"""
        self._memory_cache.clear()

        if self.enable_persistence:
            cache_file = self.cache_dir / "cache.json"
            if cache_file.exists():
                cache_file.unlink()


__all__ = ["TestGenerationCache", "CacheEntry"]
