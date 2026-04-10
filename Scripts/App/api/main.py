"""
NeetResearch App - FastAPI Backend

Main entry point for the API server.

Run with:
    cd Scripts/App
    python -m uvicorn api.main:app --reload --port 8000
"""

import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio

from Scripts.App.api.routes import research_router, sessions_router, export_router
from Scripts.App.api.websocket import manager


# Track initialization state
init_state = {
    "status": "not_started",
    "progress": 0,
    "message": "Waiting to start...",
    "ready": False
}


async def initialize_backend():
    """Initialize backend components with progress tracking."""
    global init_state
    
    try:
        init_state["status"] = "initializing"
        init_state["progress"] = 10
        init_state["message"] = "Loading environment..."
        
        # Load dotenv
        from dotenv import load_dotenv
        load_dotenv()
        await asyncio.sleep(0.1)  # Allow WebSocket updates
        
        init_state["progress"] = 30
        init_state["message"] = "Loading configuration..."
        
        # Import config to trigger initialization
        from Scripts.App.config import MODEL_CONFIG
        await asyncio.sleep(0.1)
        
        init_state["progress"] = 50
        init_state["message"] = "Initializing database tools..."

        # Pre-initialize database tools
        def _init_db():
            # from Scripts.App.database.database import RetrievalTool
            # return RetrievalTool(db_path="./database/db")
            pass # Skipped locally to prevent Render OOM
            
        _ = await asyncio.to_thread(_init_db)
        await asyncio.sleep(0.1)

        init_state["progress"] = 80
        init_state["message"] = "Building research graph..."
        
        # Pre-build the graph (optional, for faster first research)
        # from Scripts.App.graph.graph import NeetResearchAppGraph
        # _ = NeetResearchAppGraph(None)
        
        init_state["progress"] = 100
        init_state["message"] = "Ready!"
        init_state["status"] = "ready"
        init_state["ready"] = True
        
        print("✅ Backend initialization complete")
        
    except Exception as e:
        init_state["status"] = "error"
        init_state["message"] = f"Initialization failed: {str(e)}"
        print(f"❌ Backend initialization failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("🚀 Starting NeetResearch API server...")
    asyncio.create_task(initialize_backend())
    yield
    # Shutdown
    print("👋 Shutting down NeetResearch API server...")


# Create FastAPI app
app = FastAPI(
    title="NeetResearch API",
    description="Backend API for NeetResearch App - AI-powered research assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:3000", 
        "http://127.0.0.1:5173",
        "https://neet-research-app.vercel.app",
        "https://agentops-command-center.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(research_router)
app.include_router(sessions_router)
app.include_router(export_router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "name": "NeetResearch API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "initialization": init_state
    }


@app.get("/api/init-status")
async def get_init_status():
    """Get backend initialization status for progress bar."""
    return init_state


@app.websocket("/ws/research/{session_id}")
async def websocket_research(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time research updates."""
    await manager.connect(session_id, websocket)
    from Scripts.App.api.routes.research import research_sessions

    session = research_sessions.get(session_id)
    if not session:
        await websocket.send_json({
            "type": "error",
            "message": "Session not found"
        })
        manager.disconnect(session_id, websocket)
        await websocket.close(code=1008, reason="Session not found")
        return

    # Send immediate snapshot so clients always get current state on connect/reconnect.
    try:
        await websocket.send_json({
            "type": "phase_update",
            "phase": str(session.get("status", "initializing")),
            "progress": int(session.get("overall_progress", 0)),
            "message": "Connected to live research updates",
            "notes": [],
        })
    except Exception:
        # Snapshot send should never break the websocket endpoint.
        pass

    try:
        while True:
            try:
                # Keep connection open and process optional client messages.
                await asyncio.wait_for(websocket.receive_text(), timeout=25)
            except asyncio.TimeoutError:
                # Server heartbeat to keep proxies/load balancers from idling out connections.
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
    except Exception:
        manager.disconnect(session_id, websocket)


@app.websocket("/ws/init")
async def websocket_init(websocket: WebSocket):
    """WebSocket endpoint for initialization progress."""
    await websocket.accept()
    try:
        last_progress = -1
        while not init_state["ready"]:
            if init_state["progress"] != last_progress:
                await websocket.send_json(init_state)
                last_progress = init_state["progress"]
            await asyncio.sleep(0.1)
        
        # Send final ready state
        await websocket.send_json(init_state)
    except WebSocketDisconnect:
        pass


# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
