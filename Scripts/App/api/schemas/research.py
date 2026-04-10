"""
Research Schemas - Pydantic models for research endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class SourceType(str, Enum):
    """Research source type."""
    WEB = "web"
    DATABASE = "database"
    BOTH = "both"


class ResearchPhase(str, Enum):
    """Research phases for progress tracking."""
    INITIALIZING = "initializing"
    SCOPING = "scoping"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchStartRequest(BaseModel):
    """Request to start a new research session."""
    topic: str = Field(..., min_length=3, max_length=1000, description="Research topic")
    source_type: SourceType = Field(default=SourceType.WEB, description="Source type")
    collection_name: Optional[str] = Field(None, description="Database collection name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Impact of climate change on agriculture",
                "source_type": "web"
            }
        }


class ResearchStartResponse(BaseModel):
    """Response after starting research."""
    session_id: str
    topic: str
    status: ResearchPhase
    message: str
    created_at: datetime


class PhaseProgress(BaseModel):
    """Progress of a single research phase."""
    phase: ResearchPhase
    status: str  # pending, active, completed, error
    progress: int = Field(ge=0, le=100)
    message: Optional[str] = None
    notes: List[str] = []


class ResearchStatusResponse(BaseModel):
    """Current status of a research session."""
    session_id: str
    topic: str
    status: ResearchPhase
    overall_progress: int = Field(ge=0, le=100)
    phases: List[PhaseProgress]
    sources_found: int = 0
    estimated_time_remaining: Optional[int] = None  # seconds
    final_report: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ResearchCancelResponse(BaseModel):
    """Response after cancelling research."""
    session_id: str
    status: ResearchPhase
    message: str
