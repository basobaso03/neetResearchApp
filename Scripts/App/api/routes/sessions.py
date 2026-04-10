"""
Sessions Routes - API endpoints for session management
"""

from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime

from Scripts.App.api.schemas.session import (
    SessionResponse,
    SessionListResponse,
    SessionResumeResponse,
)
from Scripts.App.api.schemas.research import ResearchPhase
from Scripts.App.api.routes.research import research_sessions, run_research_task
import asyncio

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.get("", response_model=SessionListResponse)
async def list_sessions():
    """List all research sessions."""
    sessions = []
    for session_id, data in research_sessions.items():
        sessions.append(SessionResponse(
            session_id=session_id,
            topic=data["topic"],
            status=data["status"],
            progress=data["overall_progress"],
            sources_found=data["sources_found"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            is_web_research=data["is_web_research"],
            error_message=data["error_message"],
            has_report=data["final_report"] is not None
        ))
    
    # Sort by created_at descending
    sessions.sort(key=lambda s: s.created_at, reverse=True)
    
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get a specific session's details."""
    session = research_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(
        session_id=session_id,
        topic=session["topic"],
        status=session["status"],
        progress=session["overall_progress"],
        sources_found=session["sources_found"],
        created_at=session["created_at"],
        updated_at=session["updated_at"],
        source_type=session.get("source_type", "web"),
        is_web_research=session["is_web_research"],
        error_message=session["error_message"],
        has_report=session["final_report"] is not None
    )


@router.post("/{session_id}/resume", response_model=SessionResumeResponse)
async def resume_session(session_id: str):
    """Resume a paused or failed session."""
    session = research_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["status"] == ResearchPhase.COMPLETED:
        raise HTTPException(status_code=400, detail="Session already completed")
    
    if session["status"] not in [ResearchPhase.FAILED, ResearchPhase.CANCELLED]:
        raise HTTPException(status_code=400, detail="Session is not in a resumable state")
    
    # Reset status and restart
    session["status"] = ResearchPhase.INITIALIZING
    session["error_message"] = None
    session["updated_at"] = datetime.now()
    
    # Restart the research task
    task = asyncio.create_task(run_research_task(session_id))
    session["task"] = task
    
    return SessionResumeResponse(
        session_id=session_id,
        status=ResearchPhase.INITIALIZING,
        message="Session resumed successfully"
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = research_sessions[session_id]
    
    # Cancel task if running
    task = session.get("task")
    if task and not task.done():
        task.cancel()
    
    del research_sessions[session_id]
    
    return {"message": "Session deleted successfully"}
