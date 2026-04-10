"""
Research Session Manager for NeetResearch App.

Provides persistent, resumable research sessions with:
- SQLite checkpointing via LangGraph
- Session metadata tracking
- Progress monitoring
- Crash recovery
"""

import uuid
import json
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from Scripts.App.config import MODEL_CONFIG


class SessionStatus(Enum):
    """Status of a research session."""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SessionMetadata:
    """Metadata for a research session."""
    session_id: str
    topic: str
    created_at: float
    last_updated: float
    status: str
    progress_percent: int
    current_phase: str
    total_sources: int
    error_message: Optional[str] = None
    is_web_research: bool = True


class ResearchSessionManager:
    """
    Manages persistent research sessions with checkpoint support.
    
    Usage:
        manager = ResearchSessionManager()
        session = manager.create_session("Impact of AI on healthcare")
        result = await session.run()
        
        # Later, resume:
        session = manager.load_session("abc123")
        result = await session.resume()
    """
    
    def __init__(self, sessions_dir: str = "./research_sessions"):
        """
        Initialize the session manager.
        
        Args:
            sessions_dir: Directory to store session data
        """
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        print(f"📁 Sessions directory: {self.sessions_dir.absolute()}")
    
    def create_session(
        self, 
        topic: str, 
        is_web_research: bool = True
    ) -> 'ResearchSession':
        """
        Create a new research session.
        
        Args:
            topic: Research topic
            is_web_research: Whether to use web search (vs local DB)
        
        Returns:
            New ResearchSession instance
        """
        session_id = str(uuid.uuid4())[:8]
        session = ResearchSession(
            session_id=session_id,
            topic=topic,
            sessions_dir=self.sessions_dir,
            is_web_research=is_web_research
        )
        session.save_metadata()
        print(f"✅ Created session: {session_id}")
        print(f"📝 Topic: {topic[:50]}...")
        return session
    
    def list_sessions(self, status: Optional[str] = None) -> List[SessionMetadata]:
        """
        List all saved sessions.
        
        Args:
            status: Optional filter by status
        
        Returns:
            List of session metadata
        """
        sessions = []
        for meta_file in self.sessions_dir.glob("*/metadata.json"):
            try:
                with open(meta_file) as f:
                    data = json.load(f)
                    metadata = SessionMetadata(**data)
                    if status is None or metadata.status == status:
                        sessions.append(metadata)
            except Exception as e:
                print(f"⚠️ Error loading {meta_file}: {e}")
        
        return sorted(sessions, key=lambda s: s.last_updated, reverse=True)
    
    def load_session(self, session_id: str) -> 'ResearchSession':
        """
        Load an existing session.
        
        Args:
            session_id: ID of the session to load
        
        Returns:
            ResearchSession instance
        """
        session_path = self.sessions_dir / session_id
        if not session_path.exists():
            raise ValueError(f"Session {session_id} not found")
        
        with open(session_path / "metadata.json") as f:
            data = json.load(f)
            metadata = SessionMetadata(**data)
        
        session = ResearchSession(
            session_id=session_id,
            topic=metadata.topic,
            sessions_dir=self.sessions_dir,
            existing_metadata=metadata,
            is_web_research=metadata.is_web_research
        )
        print(f"📂 Loaded session: {session_id}")
        print(f"📊 Progress: {metadata.progress_percent}%")
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and its data.
        
        Args:
            session_id: ID of the session to delete
        
        Returns:
            True if deleted successfully
        """
        import shutil
        session_path = self.sessions_dir / session_id
        if session_path.exists():
            shutil.rmtree(session_path)
            print(f"🗑️ Deleted session: {session_id}")
            return True
        return False
    
    def get_resumable_sessions(self) -> List[SessionMetadata]:
        """Get sessions that can be resumed."""
        return self.list_sessions(status=SessionStatus.PAUSED.value)
    
    def get_completed_sessions(self) -> List[SessionMetadata]:
        """Get completed sessions."""
        return self.list_sessions(status=SessionStatus.COMPLETED.value)


class ResearchSession:
    """
    Individual research session with checkpointing support.
    
    Provides:
    - Automatic checkpointing after each step
    - Resume from last checkpoint on failure
    - Progress tracking and callbacks
    """
    
    def __init__(
        self, 
        session_id: str, 
        topic: str,
        sessions_dir: Path,
        existing_metadata: Optional[SessionMetadata] = None,
        is_web_research: bool = True
    ):
        self.session_id = session_id
        self.topic = topic
        self.session_path = sessions_dir / session_id
        self.session_path.mkdir(exist_ok=True)
        self.is_web_research = is_web_research
        
        # Initialize checkpointer
        self.db_path = self.session_path / "checkpoints.db"
        self._checkpointer: Optional[SqliteSaver] = None
        
        # Initialize or load metadata
        if existing_metadata:
            self.metadata = existing_metadata
        else:
            self.metadata = SessionMetadata(
                session_id=session_id,
                topic=topic,
                created_at=time.time(),
                last_updated=time.time(),
                status=SessionStatus.CREATED.value,
                progress_percent=0,
                current_phase='init',
                total_sources=0,
                is_web_research=is_web_research
            )
        
        # Graph will be built lazily
        self._graph = None
    
    @property
    def checkpointer(self) -> SqliteSaver:
        """Get or create the SQLite checkpointer."""
        if self._checkpointer is None:
            self._checkpointer = SqliteSaver.from_conn_string(str(self.db_path))
        return self._checkpointer
    
    def _build_graph(self):
        """Build research graph with checkpointing enabled."""
        from Scripts.App.graph.graph import NeetResearchAppGraph
        from Scripts.App.database.database import RetrievalTool
        
        # Create a minimal RetrievalTool for now
        # TODO: Allow passing custom RetrievalTool
        db_tools = RetrievalTool()
        
        graph_builder = NeetResearchAppGraph(db_tools)
        return graph_builder.build()
    
    @property
    def graph(self):
        """Get or build the graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph
    
    async def run(
        self, 
        max_duration: int = None,
        progress_callback: Optional[Callable[[SessionMetadata], None]] = None
    ) -> Dict[str, Any]:
        """
        Run research with automatic checkpointing.
        
        Args:
            max_duration: Maximum duration in seconds (default from config)
            progress_callback: Optional callback for progress updates
        
        Returns:
            Final research state
        """
        if max_duration is None:
            max_duration = MODEL_CONFIG.session_timeout
        
        self.metadata.status = SessionStatus.IN_PROGRESS.value
        self.save_metadata()
        
        config = {"configurable": {"thread_id": self.session_id}}
        start_time = time.time()
        
        try:
            # Build initial state
            from Scripts.App.graph.state.graph_state import AgentState
            
            initial_state = AgentState(
                messages=[HumanMessage(content=self.topic)],
                research_brief="",
                final_report="",
                notes=[],
                is_research_web=self.is_web_research
            )
            
            print(f"🚀 Starting research: {self.topic[:50]}...")
            self.metadata.current_phase = 'starting'
            self.save_metadata()
            
            # Run with timeout
            result = await asyncio.wait_for(
                self.graph.ainvoke(initial_state),
                timeout=max_duration
            )
            
            # Update final state
            self._update_progress(result)
            self.metadata.status = SessionStatus.COMPLETED.value
            self.metadata.progress_percent = 100
            self.save_metadata()
            
            print(f"✅ Research completed!")
            return result
            
        except asyncio.TimeoutError:
            print(f"⏰ Research timed out after {max_duration}s")
            self.metadata.status = SessionStatus.PAUSED.value
            self.metadata.error_message = f"Timed out after {max_duration}s"
            self.save_metadata()
            return {"error": "timeout", "partial": True}
            
        except Exception as e:
            print(f"❌ Research failed: {e}")
            self.metadata.status = SessionStatus.FAILED.value
            self.metadata.error_message = str(e)
            self.save_metadata()
            raise
    
    async def resume(
        self,
        progress_callback: Optional[Callable[[SessionMetadata], None]] = None
    ) -> Dict[str, Any]:
        """
        Resume research from last checkpoint.
        
        Args:
            progress_callback: Optional callback for progress updates
        
        Returns:
            Final research state
        """
        print(f"🔄 Resuming session {self.session_id}...")
        self.metadata.status = SessionStatus.IN_PROGRESS.value
        self.metadata.error_message = None
        self.save_metadata()
        
        return await self.run(progress_callback=progress_callback)
    
    def get_progress(self) -> SessionMetadata:
        """Get current progress."""
        return self.metadata
    
    def save_metadata(self):
        """Save session metadata to disk."""
        self.metadata.last_updated = time.time()
        meta_path = self.session_path / "metadata.json"
        with open(meta_path, 'w') as f:
            json.dump(asdict(self.metadata), f, indent=2)
    
    def _update_progress(self, state: Dict):
        """Update progress based on state."""
        notes = state.get('notes', [])
        self.metadata.total_sources = len(notes)
        
        # Estimate progress based on state
        if state.get('final_report'):
            self.metadata.progress_percent = 100
            self.metadata.current_phase = 'completed'
        elif notes:
            self.metadata.progress_percent = min(80, len(notes) * 10)
            self.metadata.current_phase = 'researching'
        elif state.get('research_brief'):
            self.metadata.progress_percent = 20
            self.metadata.current_phase = 'scoping'
        
        self.save_metadata()
    
    def export_report(self, format: str = 'txt') -> Optional[Path]:
        """
        Export the final report.
        
        Args:
            format: Export format ('txt', 'md')
        
        Returns:
            Path to exported file
        """
        # TODO: Integrate with export_report module
        report_path = self.session_path / f"report.{format}"
        # Placeholder for now
        return report_path


# Convenience functions
_session_manager: Optional[ResearchSessionManager] = None


def get_session_manager(sessions_dir: str = "./research_sessions") -> ResearchSessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = ResearchSessionManager(sessions_dir)
    return _session_manager


async def quick_research(topic: str, is_web: bool = True) -> Dict[str, Any]:
    """
    Quick convenience function to run a research session.
    
    Args:
        topic: Research topic
        is_web: Whether to use web search
    
    Returns:
        Research results
    """
    manager = get_session_manager()
    session = manager.create_session(topic, is_web_research=is_web)
    return await session.run()
