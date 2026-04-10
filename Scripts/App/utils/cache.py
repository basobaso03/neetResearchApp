"""
Caching Layer for NeetResearch App.

Provides caching for:
- LLM responses
- Search results
- Embeddings
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Optional, Any, Dict
from dataclasses import dataclass, asdict
import pickle


@dataclass
class CacheEntry:
    """A cached entry with metadata."""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float]
    hit_count: int = 0


class SimpleCache:
    """
    A simple file-based cache for LLM responses and search results.
    
    Features:
    - TTL (time-to-live) support
    - Disk persistence
    - Memory cache with LRU-style management
    """
    
    def __init__(
        self,
        cache_dir: str = "./.cache",
        default_ttl: int = 3600,  # 1 hour
        max_memory_items: int = 100
    ):
        """
        Initialize cache.
        
        Args:
            cache_dir: Directory for persistent cache
            default_ttl: Default TTL in seconds
            max_memory_items: Max items in memory cache
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.max_memory_items = max_memory_items
        
        # In-memory cache
        self._memory_cache: Dict[str, CacheEntry] = {}
        
        # Stats
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments."""
        key_data = json.dumps((args, sorted(kwargs.items())), sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for a cache key."""
        return self.cache_dir / f"{key}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            
            # Check expiration
            if entry.expires_at and time.time() > entry.expires_at:
                del self._memory_cache[key]
            else:
                entry.hit_count += 1
                self.hits += 1
                return entry.value
        
        # Check disk cache
        file_path = self._get_file_path(key)
        if file_path.exists():
            try:
                with open(file_path, 'rb') as f:
                    entry = pickle.load(f)
                
                # Check expiration
                if entry.expires_at and time.time() > entry.expires_at:
                    file_path.unlink()
                    self.misses += 1
                    return None
                
                # Load into memory cache
                self._memory_cache[key] = entry
                self._evict_if_needed()
                
                entry.hit_count += 1
                self.hits += 1
                return entry.value
                
            except Exception:
                self.misses += 1
                return None
        
        self.misses += 1
        return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = None,
        persist: bool = True
    ):
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            persist: Whether to persist to disk
        """
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl if ttl > 0 else None
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            expires_at=expires_at
        )
        
        # Store in memory
        self._memory_cache[key] = entry
        self._evict_if_needed()
        
        # Persist to disk
        if persist:
            try:
                file_path = self._get_file_path(key)
                with open(file_path, 'wb') as f:
                    pickle.dump(entry, f)
            except Exception as e:
                print(f"⚠️ Cache write failed: {e}")
    
    def _evict_if_needed(self):
        """Evict oldest entries if memory cache is too large."""
        while len(self._memory_cache) > self.max_memory_items:
            # Remove least recently used (by hit count)
            oldest_key = min(
                self._memory_cache.keys(),
                key=lambda k: self._memory_cache[k].hit_count
            )
            del self._memory_cache[oldest_key]
    
    def delete(self, key: str):
        """Delete a cached entry."""
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        file_path = self._get_file_path(key)
        if file_path.exists():
            file_path.unlink()
    
    def clear(self):
        """Clear all cache entries."""
        self._memory_cache.clear()
        for f in self.cache_dir.glob("*.cache"):
            f.unlink()
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1%}",
            "memory_items": len(self._memory_cache),
            "disk_items": len(list(self.cache_dir.glob("*.cache"))),
        }


class LLMCache(SimpleCache):
    """
    Specialized cache for LLM responses.
    """
    
    def __init__(self, cache_dir: str = "./.cache/llm"):
        super().__init__(
            cache_dir=cache_dir,
            default_ttl=86400,  # 24 hours for LLM responses
            max_memory_items=50
        )
    
    def get_response(
        self,
        prompt: str,
        model: str,
        temperature: float = 0
    ) -> Optional[str]:
        """
        Get cached LLM response.
        
        Args:
            prompt: LLM prompt
            model: Model name
            temperature: Model temperature
            
        Returns:
            Cached response or None
        """
        key = self._make_key(prompt, model=model, temp=temperature)
        return self.get(key)
    
    def set_response(
        self,
        prompt: str,
        model: str,
        response: str,
        temperature: float = 0
    ):
        """
        Cache an LLM response.
        
        Args:
            prompt: LLM prompt
            model: Model name
            response: LLM response
            temperature: Model temperature
        """
        key = self._make_key(prompt, model=model, temp=temperature)
        self.set(key, response)


class SearchCache(SimpleCache):
    """
    Specialized cache for search results.
    """
    
    def __init__(self, cache_dir: str = "./.cache/search"):
        super().__init__(
            cache_dir=cache_dir,
            default_ttl=3600,  # 1 hour for search results
            max_memory_items=100
        )
    
    def get_results(self, query: str) -> Optional[list]:
        """
        Get cached search results.
        
        Args:
            query: Search query
            
        Returns:
            Cached results or None
        """
        key = self._make_key(query.lower().strip())
        return self.get(key)
    
    def set_results(self, query: str, results: list):
        """
        Cache search results.
        
        Args:
            query: Search query
            results: Search results
        """
        key = self._make_key(query.lower().strip())
        self.set(key, results)


# Global cache instances
_llm_cache: Optional[LLMCache] = None
_search_cache: Optional[SearchCache] = None


def get_llm_cache() -> LLMCache:
    """Get the global LLM cache instance."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
    return _llm_cache


def get_search_cache() -> SearchCache:
    """Get the global search cache instance."""
    global _search_cache
    if _search_cache is None:
        _search_cache = SearchCache()
    return _search_cache


def cached_llm_call(prompt: str, model: str, temperature: float = 0):
    """
    Decorator-style function for cached LLM calls.
    
    Usage:
        cached = cached_llm_call(prompt, "gemini-2.5-flash", 0)
        if cached:
            return cached
        # ... make actual LLM call
        get_llm_cache().set_response(prompt, model, response)
    """
    cache = get_llm_cache()
    return cache.get_response(prompt, model, temperature)
