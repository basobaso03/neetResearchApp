"""
API Key Manager for NeetResearch App.

This module provides:
- Centralized API key management
- Round-robin key rotation
- Task-based key distribution
- Secure key loading from environment
"""

import os
import itertools
import re
from typing import Optional, List, Iterator
from dataclasses import dataclass, field
import dotenv

# Load environment variables
dotenv.load_dotenv()


@dataclass
class APIKey:
    """Represents a single API key with metadata."""
    name: str
    env_var: str
    priority: int = 0
    is_active: bool = True
    value: Optional[str] = None
    
    def __post_init__(self):
        """Load key value from environment."""
        self.value = os.getenv(self.env_var)
        if self.value and self.value.startswith("AIza"):
            self.is_active = True
        else:
            self.is_active = False


class APIKeyManager:
    """
    Manages multiple API keys with rotation and fallback.
    
    Features:
    - Round-robin rotation across keys
    - Task-specific key assignment
    - Automatic validation
    - Fallback on rate limits
    """
    
    def __init__(self):
        # Define all available keys
        self._key_definitions = [
            APIKey("Main", "GOOGLE_API_KEY", priority=0),
            APIKey("Takunda", "Takunda_api_key", priority=1),
            APIKey("Kudzaishe", "kudzaishe_api_key", priority=2),
            APIKey("Patience", "patience_api_key", priority=3),
            APIKey("Nigel", "Nigel_api_key", priority=4),
        ]
        self._discover_additional_keys()
        
        self.active_keys: List[APIKey] = []
        self._cycler: Optional[Iterator[APIKey]] = None
        self._task_cyclers: dict = {}
        
        self._load_keys()
        self._create_cycler()

    def _discover_additional_keys(self):
        """Discover additional API key env vars and add them to rotation."""
        known_envs = {k.env_var.lower() for k in self._key_definitions}
        next_priority = max(k.priority for k in self._key_definitions) + 1

        for env_name in sorted(os.environ.keys()):
            lowered = env_name.lower()
            if lowered in known_envs:
                continue

            is_google_key = bool(re.match(r"^google_api_key\d*$", lowered))
            is_named_api_key = lowered.endswith("_api_key")
            if not (is_google_key or is_named_api_key):
                continue

            # Exclude non-primary helper variables.
            if lowered == "google_api_key_without_cse":
                continue

            self._key_definitions.append(APIKey(env_name, env_name, priority=next_priority))
            next_priority += 1
    
    def _load_keys(self):
        """Load and validate keys from environment."""
        self.active_keys = []
        seen_values = set()
        
        for key in sorted(self._key_definitions, key=lambda k: k.priority):
            if key.is_active and key.value:
                if key.value in seen_values:
                    continue
                self.active_keys.append(key)
                seen_values.add(key.value)
                print(f"Loaded API key: {key.name}")
            else:
                print(f"WARNING: API key not found or invalid: {key.name} ({key.env_var})")
        
        if not self.active_keys:
            raise ValueError(
                "No valid API keys found! Please set at least one of: "
                "GOOGLE_API_KEY, Takunda_api_key, kudzaishe_api_key, "
                "patience_api_key, Nigel_api_key"
            )
        
        print(f"Total active keys: {len(self.active_keys)}")
    
    def _create_cycler(self):
        """Create round-robin cycler for keys."""
        self._cycler = itertools.cycle(self.active_keys)
    
    def get_next_key(self) -> str:
        """
        Get the next key in round-robin rotation.
        
        Returns:
            API key string
        """
        if not self._cycler:
            self._create_cycler()
        
        key = next(self._cycler)
        return key.value
    
    def get_key_for_task(self, task_type: str) -> str:
        """
        Get a specific key for a task type.
        
        Distributes tasks across keys to maximize throughput:
        - Each task type gets its own key rotation
        - This prevents all tasks hitting the same key
        
        Args:
            task_type: Type of task (e.g., 'scoping', 'research')
        
        Returns:
            API key string
        """
        # Task-to-key preference mapping
        task_key_preferences = {
            "scoping": "Takunda",
            "clarification": "Takunda",
            "research": "Kudzaishe",
            "supervisor": "Patience",
            "compression": "Nigel",
            "summarization": "Main",
            "export": "Main",
            "report": "Kudzaishe",
        }
        
        # Create task-specific cycler if not exists.
        if task_type not in self._task_cyclers:
            preferred_name = task_key_preferences.get(task_type)
            ordered_keys = []

            if preferred_name:
                ordered_keys.extend([k for k in self.active_keys if k.name == preferred_name])

            ordered_keys.extend([k for k in self.active_keys if k not in ordered_keys])
            if not ordered_keys:
                ordered_keys = self.active_keys

            self._task_cyclers[task_type] = itertools.cycle(ordered_keys)
        
        key = next(self._task_cyclers[task_type])
        return key.value
    
    def get_all_keys(self) -> List[str]:
        """Get all active API keys."""
        return [k.value for k in self.active_keys if k.value]
    
    def get_key_count(self) -> int:
        """Get number of active keys."""
        return len(self.active_keys)
    
    def mark_key_limited(self, key_value: str, duration: int = 60):
        """
        Mark a key as rate-limited (for future rate limit handling).
        
        Args:
            key_value: The API key that hit rate limit
            duration: Seconds to wait before using again
        """
        # TODO: Implement rate limit tracking
        pass


# Global instance
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """Get the global API key manager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


def get_api_key(task: str = None) -> str:
    """
    Convenience function to get an API key.
    
    Args:
        task: Optional task name for task-specific key selection
    
    Returns:
        API key string
    """
    manager = get_api_key_manager()
    if task:
        return manager.get_key_for_task(task)
    return manager.get_next_key()
