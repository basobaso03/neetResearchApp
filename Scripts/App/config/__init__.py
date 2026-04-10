"""
Configuration package for NeetResearch App.

Provides centralized configuration for:
- LLM models and settings
- API key management
- Rate limiting
- Reliability utilities
"""

from .llm_config import (
    MODEL_CONFIG,
    ModelConfig,
    TaskComplexity,
    TASK_MODEL_MAP,
    get_model_for_task,
    get_fallback_models,
)

from .api_key_manager import (
    APIKeyManager,
    get_api_key_manager,
    get_api_key,
)

from .rate_limiter import (
    AdaptiveRateLimiter,
    get_rate_limiter,
    acquire_rate_limit,
    report_rate_limit_error,
)

from .reliability import (
    with_timeout,
    with_retry,
    run_with_timeout,
    run_with_retry,
    RetryableError,
    NonRetryableError,
)

# Aliases for compatibility
RateLimiter = AdaptiveRateLimiter
retry_with_backoff = with_retry

# RetryConfig dataclass
from dataclasses import dataclass

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0

__all__ = [
    # LLM Config
    "MODEL_CONFIG",
    "ModelConfig", 
    "TaskComplexity",
    "TASK_MODEL_MAP",
    "get_model_for_task",
    "get_fallback_models",
    # API Key Manager
    "APIKeyManager",
    "get_api_key_manager",
    "get_api_key",
    # Rate Limiter
    "AdaptiveRateLimiter",
    "RateLimiter",  # Alias
    "get_rate_limiter",
    "acquire_rate_limit",
    "report_rate_limit_error",
    # Reliability
    "with_timeout",
    "with_retry",
    "retry_with_backoff",  # Alias
    "run_with_timeout",
    "run_with_retry",
    "RetryableError",
    "NonRetryableError",
    "RetryConfig",
]
