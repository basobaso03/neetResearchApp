"""
Centralized LLM Configuration for NeetResearch App.

This module provides:
- Model selection by task complexity
- Optimized model pools for free tier usage
- Centralized configuration to avoid duplication
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
import os


class TaskComplexity(Enum):
    """Task complexity levels for model selection."""
    SIMPLE = "simple"      # Clarification, formatting, metadata
    MEDIUM = "medium"      # Summarization, research compression
    COMPLEX = "complex"    # Report generation, deep analysis, supervision


@dataclass
class ModelConfig:
    """
    Centralized model configuration for free tier optimization.
    
    Models are organized by task complexity to optimize API usage:
    - Simple tasks use Flash-Lite (3x more RPM on free tier)
    - Medium tasks use Flash (balanced)
    - Complex tasks use Flash with fallbacks
    """
    
    # Model pools by complexity
    simple_models: List[str] = field(default_factory=lambda: [
        "gemini-2.5-flash-lite",
    ])
    
    medium_models: List[str] = field(default_factory=lambda: [
        "gemini-2.5-flash-lite",
    ])
    
    complex_models: List[str] = field(default_factory=lambda: [
        "gemini-2.5-flash-lite",
    ])
    
    # Supervisor-specific models
    supervisor_models: List[str] = field(default_factory=lambda: [
        "gemini-2.5-flash-lite",
    ])
    
    # Research agent models (excludes expensive ones)
    research_models: List[str] = field(default_factory=lambda: [
        "gemini-2.5-flash-lite",
    ])
    
    # Export models (simple task)
    export_models: List[str] = field(default_factory=lambda: [
        "gemini-2.5-flash-lite",
    ])
    
    # Default timeouts (in seconds)
    llm_timeout: int = 120  # 2 minutes
    step_timeout: int = 300  # 5 minutes
    session_timeout: int = 3600  # 1 hour
    
    # Rate limiting
    requests_per_minute: int = 5
    max_retries: int = 3
    retry_delay: float = 2.0
    
    # Graph limits
    recursion_limit: int = 50
    max_messages: int = 20
    
    def get_models_for_task(self, complexity: TaskComplexity) -> List[str]:
        """Get appropriate models for a given task complexity."""
        if complexity == TaskComplexity.SIMPLE:
            return self.simple_models
        elif complexity == TaskComplexity.MEDIUM:
            return self.medium_models
        else:
            return self.complex_models
    
    def get_models_for_role(self, role: str) -> List[str]:
        """Get models for a specific agent role."""
        role_map = {
            "supervisor": self.supervisor_models,
            "research": self.research_models,
            "scoping": self.simple_models,
            "compression": self.medium_models,
            "export": self.export_models,
            "summarization": self.medium_models,
            "report": self.complex_models,
        }
        return role_map.get(role, self.medium_models)


# Global configuration instance
MODEL_CONFIG = ModelConfig()


# Task-to-model mapping for easy reference
TASK_MODEL_MAP = {
    # Simple tasks - use Flash-Lite
    "scoping": TaskComplexity.SIMPLE,
    "clarification": TaskComplexity.SIMPLE,
    "metadata_extraction": TaskComplexity.SIMPLE,
    "formatting": TaskComplexity.SIMPLE,
    "export": TaskComplexity.SIMPLE,
    
    # Medium tasks - use Flash
    "summarization": TaskComplexity.MEDIUM,
    "compression": TaskComplexity.MEDIUM,
    "web_search": TaskComplexity.MEDIUM,
    "db_search": TaskComplexity.MEDIUM,
    
    # Complex tasks - use Flash with care
    "supervision": TaskComplexity.COMPLEX,
    "report_generation": TaskComplexity.COMPLEX,
    "deep_analysis": TaskComplexity.COMPLEX,
}


def get_model_for_task(task_name: str) -> str:
    """
    Get the primary model for a specific task.
    
    Args:
        task_name: Name of the task (e.g., 'scoping', 'summarization')
    
    Returns:
        The primary model name string
    """
    complexity = TASK_MODEL_MAP.get(task_name, TaskComplexity.MEDIUM)
    models = MODEL_CONFIG.get_models_for_task(complexity)
    return models[0] if models else "gemini-2.5-flash"


def get_fallback_models(task_name: str) -> List[str]:
    """
    Get fallback models for a specific task.
    
    Args:
        task_name: Name of the task
    
    Returns:
        List of fallback model names (excluding primary)
    """
    complexity = TASK_MODEL_MAP.get(task_name, TaskComplexity.MEDIUM)
    models = MODEL_CONFIG.get_models_for_task(complexity)
    return models[1:] if len(models) > 1 else []
