"""
Sessions package for NeetResearch App.

Provides:
- ResearchSessionManager: Manage multiple sessions
- ResearchSession: Individual session with checkpointing
- MemoryManager: Rolling summarization for long research
"""

from .research_session import (
    ResearchSessionManager,
    ResearchSession,
    SessionMetadata,
    SessionStatus,
    get_session_manager,
    quick_research,
)

from .memory_manager import (
    RollingMemory,
    MemoryManager,
)

__all__ = [
    # Session Management
    "ResearchSessionManager",
    "ResearchSession", 
    "SessionMetadata",
    "SessionStatus",
    "get_session_manager",
    "quick_research",
    # Memory Management
    "RollingMemory",
    "MemoryManager",
]
