"""
Reliability utilities for NeetResearch App.

Provides decorators and wrappers for:
- Timeout handling
- Retry logic with exponential backoff
- Error recovery
"""

import asyncio
from functools import wraps
from typing import TypeVar, Callable, Any, Optional
import time

T = TypeVar('T')


def with_timeout(timeout_seconds: int = 300):
    """
    Decorator to add timeout to async functions.
    
    Args:
        timeout_seconds: Maximum time allowed for function execution
    
    Usage:
        @with_timeout(120)
        async def my_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                func_name = func.__name__
                print(f"⚠️ {func_name} timed out after {timeout_seconds}s")
                raise TimeoutError(f"{func_name} timed out after {timeout_seconds} seconds")
        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3, 
    delay: float = 2.0,
    exponential_backoff: bool = True,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to add retry logic to async functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        exponential_backoff: Whether to use exponential backoff
        exceptions: Tuple of exception types to retry on
    
    Usage:
        @with_retry(max_attempts=3, delay=2.0)
        async def my_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        print(f"⚠️ Attempt {attempt + 1}/{max_attempts} failed: {e}")
                        print(f"   Retrying in {current_delay:.1f}s...")
                        await asyncio.sleep(current_delay)
                        if exponential_backoff:
                            current_delay *= 2
                    else:
                        print(f"❌ All {max_attempts} attempts failed")
            
            raise last_error
        return wrapper
    return decorator


async def run_with_timeout(
    coro,
    timeout: int = 300,
    fallback: Any = None,
    on_timeout: Optional[Callable] = None
) -> Any:
    """
    Run a coroutine with timeout and optional fallback.
    
    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
        fallback: Value to return on timeout
        on_timeout: Optional callback on timeout
    
    Returns:
        Result of coroutine or fallback value
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        print(f"⚠️ Operation timed out after {timeout}s")
        if on_timeout:
            on_timeout()
        return fallback


async def run_with_retry(
    coro_factory: Callable,
    max_attempts: int = 3,
    delay: float = 2.0,
    on_error: Optional[Callable] = None
) -> Any:
    """
    Run a coroutine with retry logic.
    
    Args:
        coro_factory: Factory function that creates the coroutine
        max_attempts: Maximum attempts
        delay: Delay between retries
        on_error: Optional callback on each error
    
    Returns:
        Result of successful coroutine execution
    """
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except Exception as e:
            last_error = e
            if on_error:
                on_error(e, attempt)
            if attempt < max_attempts - 1:
                print(f"⚠️ Attempt {attempt + 1}/{max_attempts} failed: {e}")
                await asyncio.sleep(delay)
    
    raise last_error


class RetryableError(Exception):
    """Exception that should trigger a retry."""
    pass


class NonRetryableError(Exception):
    """Exception that should not trigger a retry."""
    pass
