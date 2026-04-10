"""
Research Routes - API endpoints for research operations
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
import uuid
import asyncio
from datetime import datetime
import hashlib

from Scripts.App.api.schemas.research import (
    ResearchStartRequest,
    ResearchStartResponse,
    ResearchStatusResponse,
    ResearchCancelResponse,
    ResearchPhase,
    PhaseProgress,
)
from Scripts.App.api.websocket import manager
from Scripts.App.utils import get_search_cache

router = APIRouter(prefix="/api/research", tags=["Research"])

RESEARCH_TASK_TIMEOUT_SECONDS = 90

# In-memory session storage
research_sessions: Dict[str, Dict[str, Any]] = {}

FINAL_REPORT_CACHE_PREFIX = "final_report"


def _final_report_cache_key(topic: str, source_type: str, collection_name: str = None) -> str:
    """Generate a stable cache key for final report outputs."""
    normalized_topic = (topic or "").strip().lower()
    normalized_source = (source_type or "web").strip().lower()
    normalized_collection = (collection_name or "").strip().lower()
    raw_key = f"{FINAL_REPORT_CACHE_PREFIX}|{normalized_topic}|{normalized_source}|{normalized_collection}"
    digest = hashlib.md5(raw_key.encode("utf-8")).hexdigest()
    return f"{FINAL_REPORT_CACHE_PREFIX}:{digest}"


def _build_cached_completed_session(
    session_id: str,
    topic: str,
    source_type: str,
    collection_name: str,
    final_report: str,
) -> Dict[str, Any]:
    """Create a completed session payload when a cached final report is found."""
    now = datetime.now()
    return {
        "session_id": session_id,
        "topic": topic,
        "source_type": source_type,
        "collection_name": collection_name,
        "status": ResearchPhase.COMPLETED,
        "overall_progress": 100,
        "phases": [
            {"phase": ResearchPhase.SCOPING, "status": "completed", "progress": 100, "notes": ["Loaded from final report cache."]},
            {"phase": ResearchPhase.RESEARCHING, "status": "completed", "progress": 100, "notes": ["Loaded from final report cache."]},
            {"phase": ResearchPhase.ANALYZING, "status": "completed", "progress": 100, "notes": ["Loaded from final report cache."]},
            {"phase": ResearchPhase.GENERATING, "status": "completed", "progress": 100, "notes": ["Loaded from final report cache."]},
        ],
        "sources_found": 0,
        "final_report": final_report,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
        "is_web_research": source_type == "web",
        "task": None,
    }


def create_session_data(session_id: str, topic: str, source_type: str, collection_name: str = None) -> Dict:
    """Create initial session data structure."""
    now = datetime.now()
    return {
        "session_id": session_id,
        "topic": topic,
        "source_type": source_type,
        "collection_name": collection_name,
        "status": ResearchPhase.INITIALIZING,
        "overall_progress": 0,
        "phases": [
            {"phase": ResearchPhase.SCOPING, "status": "pending", "progress": 0, "notes": []},
            {"phase": ResearchPhase.RESEARCHING, "status": "pending", "progress": 0, "notes": []},
            {"phase": ResearchPhase.ANALYZING, "status": "pending", "progress": 0, "notes": []},
            {"phase": ResearchPhase.GENERATING, "status": "pending", "progress": 0, "notes": []},
        ],
        "sources_found": 0,
        "final_report": None,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
        "is_web_research": source_type == "web",
        "task": None,  # asyncio task reference
    }


async def run_research_task(session_id: str):
    """
    Background task that runs the actual research.
    Updates the session state and broadcasts WebSocket updates.
    """
    session = research_sessions.get(session_id)
    if not session:
        return

    def append_phase_note(phase_index: int, note: str):
        session["phases"][phase_index]["notes"].append(note)
        session["updated_at"] = datetime.now()

    async def complete_with_web_fallback(reason: str):
        """Fallback completion path when graph research fails or times out."""
        from Scripts.App.tools.adk_web_research import web_search_tool as adk_web_tool

        append_phase_note(1, f"Primary research pipeline fallback triggered: {reason}")
        fallback_report = await adk_web_tool.ainvoke({"query": session["topic"]})
        if not isinstance(fallback_report, str) or not fallback_report.strip():
            raise RuntimeError("Fallback web report generation returned no content")

        session["status"] = ResearchPhase.COMPLETED
        session["phases"][1]["status"] = "completed"
        session["phases"][1]["progress"] = 100
        session["phases"][2]["status"] = "completed"
        session["phases"][2]["progress"] = 100
        session["phases"][3]["status"] = "completed"
        session["phases"][3]["progress"] = 100
        session["overall_progress"] = 100
        session["sources_found"] = max(session.get("sources_found", 0), 1)
        session["final_report"] = fallback_report
        session["error_message"] = None
        session["updated_at"] = datetime.now()

        cache_key = _final_report_cache_key(
            topic=session.get("topic", ""),
            source_type=session.get("source_type", "web"),
            collection_name=session.get("collection_name"),
        )
        get_search_cache().set(cache_key, session["final_report"], ttl=6 * 3600)

        await manager.send_completion(session_id, session["final_report"])
        return
    
    try:
        from Scripts.App.graph.graph import NeetResearchAppGraph
        from Scripts.App.database.database import RetrievalTool
        from langchain_core.messages import HumanMessage

        # Phase 1: Initializing
        session["status"] = ResearchPhase.INITIALIZING
        session["overall_progress"] = 5
        append_phase_note(0, "Setting up research environment...")
        await manager.send_phase_update(session_id, "initializing", 5, "Setting up research environment...", session["phases"][0]["notes"])
        
        # Initialize database tools
        db_tools = RetrievalTool(db_path="./database/db")
        append_phase_note(0, "Database tools initialized.")
        
        # Build the graph
        await manager.send_phase_update(session_id, "initializing", 15, "Building research graph...", session["phases"][0]["notes"])
        neet_research_app = NeetResearchAppGraph(db_tools).build()
        append_phase_note(0, "Research graph built.")
        
        # Phase 2: Scoping
        session["status"] = ResearchPhase.SCOPING
        session["phases"][0]["status"] = "active"
        session["overall_progress"] = 20
        if session.get("source_type") == "both":
            append_phase_note(0, "Hybrid mode enabled: using web search and database tools.")
        await manager.send_phase_update(session_id, "scoping", 20, "Analyzing research topic...", session["phases"][0]["notes"])
        
        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=session["topic"])],
            "is_research_web": session["is_web_research"]
        }
        
        # Phase 3: Researching - Run the actual research
        session["status"] = ResearchPhase.RESEARCHING
        session["phases"][0]["status"] = "completed"
        session["phases"][0]["progress"] = 100
        session["phases"][1]["status"] = "active"
        session["overall_progress"] = 40
        await manager.send_phase_update(session_id, "researching", 40, "Gathering sources and information...", session["phases"][1]["notes"])
        
        # Execute the research graph with a hard timeout to avoid indefinite "researching" sessions.
        try:
            final_state = await asyncio.wait_for(
                neet_research_app.ainvoke(initial_state),
                timeout=RESEARCH_TASK_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            await complete_with_web_fallback(
                f"Research exceeded {RESEARCH_TASK_TIMEOUT_SECONDS} seconds and was stopped."
            )
            return
        research_notes = final_state.get("notes", []) or []
        session["sources_found"] = len(research_notes)
        if research_notes:
            session["phases"][1]["notes"].extend(research_notes[:10])
            append_phase_note(1, f"Collected {len(research_notes)} research notes.")
        else:
            append_phase_note(1, "No research notes were returned.")
        
        # Phase 4: Analyzing
        session["status"] = ResearchPhase.ANALYZING
        session["phases"][1]["status"] = "completed"
        session["phases"][1]["progress"] = 100
        session["phases"][2]["status"] = "active"
        session["overall_progress"] = 70
        append_phase_note(2, "Analyzing gathered findings.")
        await manager.send_phase_update(session_id, "analyzing", 70, "Analyzing findings...", session["phases"][2]["notes"])
        
        # Phase 5: Generating Report
        session["status"] = ResearchPhase.GENERATING
        session["phases"][2]["status"] = "completed"
        session["phases"][2]["progress"] = 100
        session["phases"][3]["status"] = "active"
        session["overall_progress"] = 90
        append_phase_note(3, "Generating final report.")
        await manager.send_phase_update(session_id, "generating", 90, "Generating final report...", session["phases"][3]["notes"])
        
        # Complete
        session["status"] = ResearchPhase.COMPLETED
        session["phases"][3]["status"] = "completed"
        session["phases"][3]["progress"] = 100
        session["overall_progress"] = 100
        session["final_report"] = final_state.get("final_report", "No report generated")
        session["updated_at"] = datetime.now()

        # Persist final report in cache for deterministic replay of identical requests.
        cache_key = _final_report_cache_key(
            topic=session.get("topic", ""),
            source_type=session.get("source_type", "web"),
            collection_name=session.get("collection_name"),
        )
        get_search_cache().set(cache_key, session["final_report"], ttl=6 * 3600)
        
        await manager.send_completion(session_id, session["final_report"])
        
    except asyncio.CancelledError:
        session["status"] = ResearchPhase.CANCELLED
        session["error_message"] = "Research was cancelled"
        await manager.send_error(session_id, "Research was cancelled")
        
    except Exception as e:
        # Last-resort fallback for known supervisor-note failure mode.
        if "No usable web research notes were produced" in str(e):
            try:
                await complete_with_web_fallback(str(e))
                return
            except Exception as fallback_error:
                session["status"] = ResearchPhase.FAILED
                session["error_message"] = f"{e} | fallback_error: {fallback_error}"
                session["updated_at"] = datetime.now()
                await manager.send_error(session_id, session["error_message"])
                return

        session["status"] = ResearchPhase.FAILED
        session["error_message"] = str(e)
        session["updated_at"] = datetime.now()
        await manager.send_error(session_id, str(e))


@router.post("/start", response_model=ResearchStartResponse)
async def start_research(request: ResearchStartRequest, background_tasks: BackgroundTasks):
    """Start a new research session."""
    session_id = str(uuid.uuid4())[:8]

    cache_key = _final_report_cache_key(
        topic=request.topic,
        source_type=request.source_type.value,
        collection_name=request.collection_name,
    )
    cached_final_report = get_search_cache().get(cache_key)
    if isinstance(cached_final_report, str) and cached_final_report.strip():
        cached_session = _build_cached_completed_session(
            session_id=session_id,
            topic=request.topic,
            source_type=request.source_type.value,
            collection_name=request.collection_name,
            final_report=cached_final_report,
        )
        research_sessions[session_id] = cached_session
        await manager.send_completion(session_id, cached_final_report)

        return ResearchStartResponse(
            session_id=session_id,
            topic=request.topic,
            status=ResearchPhase.COMPLETED,
            message="Research loaded from cache",
            created_at=cached_session["created_at"],
        )
    
    # Create session data
    session_data = create_session_data(
        session_id=session_id,
        topic=request.topic,
        source_type=request.source_type.value,
        collection_name=request.collection_name
    )
    research_sessions[session_id] = session_data
    
    # Start research in background
    task = asyncio.create_task(run_research_task(session_id))
    session_data["task"] = task
    
    return ResearchStartResponse(
        session_id=session_id,
        topic=request.topic,
        status=ResearchPhase.INITIALIZING,
        message="Research started successfully",
        created_at=session_data["created_at"]
    )


@router.get("/{session_id}/status", response_model=ResearchStatusResponse)
async def get_research_status(session_id: str):
    """Get the current status of a research session."""
    session = research_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    phases = [
        PhaseProgress(
            phase=p["phase"],
            status=p["status"],
            progress=p["progress"],
            notes=p.get("notes", [])
        )
        for p in session["phases"]
    ]
    
    return ResearchStatusResponse(
        session_id=session_id,
        topic=session["topic"],
        status=session["status"],
        overall_progress=session["overall_progress"],
        phases=phases,
        sources_found=session["sources_found"],
        final_report=session["final_report"],
        error_message=session["error_message"],
        created_at=session["created_at"],
        updated_at=session["updated_at"]
    )


@router.post("/{session_id}/cancel", response_model=ResearchCancelResponse)
async def cancel_research(session_id: str):
    """Cancel an ongoing research session."""
    session = research_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["status"] in [ResearchPhase.COMPLETED, ResearchPhase.FAILED, ResearchPhase.CANCELLED]:
        raise HTTPException(status_code=400, detail="Research already finished")
    
    # Cancel the background task
    task = session.get("task")
    if task and not task.done():
        task.cancel()
    
    session["status"] = ResearchPhase.CANCELLED
    session["updated_at"] = datetime.now()
    
    return ResearchCancelResponse(
        session_id=session_id,
        status=ResearchPhase.CANCELLED,
        message="Research cancelled successfully"
    )
