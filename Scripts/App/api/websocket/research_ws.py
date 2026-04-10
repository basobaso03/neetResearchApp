"""
WebSocket Manager for real-time research updates
"""

from fastapi import WebSocket
from typing import Dict, List, Optional
import json
import asyncio


class ResearchWebSocketManager:
    """
    Manages WebSocket connections for real-time research progress updates.
    
    Usage:
        # In route handler:
        await manager.connect(session_id, websocket)
        
        # In research process:
        await manager.broadcast(session_id, {"phase": "researching", "progress": 50})
    """
    
    def __init__(self):
        # session_id -> list of connected websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept a WebSocket connection for a session."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        print(f"📡 WebSocket connected for session: {session_id}")
    
    def disconnect(self, session_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        print(f"📡 WebSocket disconnected for session: {session_id}")
    
    async def broadcast(self, session_id: str, message: dict):
        """Send a message to all connected clients for a session."""
        if session_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[session_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)
            
            # Clean up disconnected clients
            for ws in disconnected:
                self.disconnect(session_id, ws)
    
    async def send_phase_update(
        self, 
        session_id: str, 
        phase: str, 
        progress: int,
        message: Optional[str] = None,
        notes: Optional[List[str]] = None
    ):
        """Send a phase progress update."""
        await self.broadcast(session_id, {
            "type": "phase_update",
            "phase": phase,
            "progress": progress,
            "message": message,
            "notes": notes or []
        })
    
    async def send_note(self, session_id: str, note: str):
        """Send a new research note."""
        await self.broadcast(session_id, {
            "type": "note",
            "content": note
        })
    
    async def send_completion(self, session_id: str, report: str):
        """Send research completion with final report."""
        await self.broadcast(session_id, {
            "type": "completed",
            "report": report
        })
    
    async def send_error(self, session_id: str, error: str):
        """Send an error message."""
        await self.broadcast(session_id, {
            "type": "error",
            "message": error
        })


# Global WebSocket manager instance
manager = ResearchWebSocketManager()
