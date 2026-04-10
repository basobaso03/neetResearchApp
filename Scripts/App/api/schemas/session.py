"""
Session Schemas - Pydantic models for session endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .research import ResearchPhase
from .research import SourceType


class SessionResponse(BaseModel):
    """Single session details."""
    session_id: str
    topic: str
    status: ResearchPhase
    progress: int = Field(ge=0, le=100)
    sources_found: int = 0
    created_at: datetime
    updated_at: datetime
    source_type: SourceType = SourceType.WEB
    is_web_research: bool = True
    error_message: Optional[str] = None
    has_report: bool = False


class SessionListResponse(BaseModel):
    """List of sessions."""
    sessions: List[SessionResponse]
    total: int


class SessionResumeResponse(BaseModel):
    """Response after resuming a session."""
    session_id: str
    status: ResearchPhase
    message: str
