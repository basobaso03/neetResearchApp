"""
Export Routes - API endpoints for exporting research reports
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import os

from Scripts.App.api.routes.research import research_sessions
from Scripts.App.api.schemas.research import ResearchPhase

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("/{session_id}")
async def export_report(session_id: str, format: str = "md"):
    """
    Export a research report.
    
    Args:
        session_id: The session ID
        format: Export format (md, pdf)
    """
    session = research_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["status"] != ResearchPhase.COMPLETED:
        raise HTTPException(status_code=400, detail="Research not yet completed")
    
    if not session["final_report"]:
        raise HTTPException(status_code=400, detail="No report available")
    
    # Import export functions
    from Scripts.App.export.export_report import free_export, smart_export
    
    # Generate safe filename from topic
    safe_topic = "".join(c if c.isalnum() or c in " -_" else "" for c in session["topic"])
    safe_topic = safe_topic[:50].strip()
    filename = f"research_{session_id}_{safe_topic}"
    
    if format == "md":
        # Free markdown export
        output_path = free_export(session["final_report"], filename)
    elif format == "pdf":
        # PDF export (uses API)
        output_path = smart_export(session["final_report"], filename, "pdf", use_llm=False)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Export failed")
    
    return FileResponse(
        path=output_path,
        filename=os.path.basename(output_path),
        media_type="application/octet-stream"
    )


@router.get("/{session_id}/content")
async def get_report_content(session_id: str):
    """Get the raw report content as JSON."""
    session = research_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session["final_report"]:
        raise HTTPException(status_code=400, detail="No report available")
    
    return {
        "session_id": session_id,
        "topic": session["topic"],
        "content": session["final_report"],
        "created_at": session["created_at"].isoformat(),
    }
