"""Session manager for FlowCheck.

Provides session tracking across MCP tool calls for audit correlation.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Session:
    """Represents an active FlowCheck session."""
    
    session_id: str
    agent_id: str
    started_at: datetime
    tool_calls: int = 0
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "started_at": self.started_at.isoformat(),
            "tool_calls": self.tool_calls,
            "last_activity": self.last_activity.isoformat(),
            "duration_seconds": int((self.last_activity - self.started_at).total_seconds()),
            "metadata": self.metadata,
        }
    
    def record_tool_call(self):
        """Record a tool call in this session."""
        self.tool_calls += 1
        self.last_activity = datetime.now(timezone.utc)


class SessionManager:
    """Manages FlowCheck sessions.
    
    Thread-safe singleton that tracks the current session.
    """
    
    _instance: Optional["SessionManager"] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._current_session: Optional[Session] = None
        self._session_lock = threading.Lock()
        self._initialized = True
    
    def start_session(self, agent_id: str = "", metadata: Optional[dict] = None) -> Session:
        """Start a new session.
        
        Args:
            agent_id: Identifier for the agent (optional).
            metadata: Additional session metadata.
            
        Returns:
            The new Session object.
        """
        with self._session_lock:
            self._current_session = Session(
                session_id=uuid.uuid4().hex[:16],
                agent_id=agent_id or "anonymous",
                started_at=datetime.now(timezone.utc),
                metadata=metadata or {},
            )
            return self._current_session
    
    def get_current_session(self) -> Optional[Session]:
        """Get the current session if one is active.
        
        Returns:
            The current Session or None.
        """
        with self._session_lock:
            return self._current_session
    
    def get_or_create_session(self, agent_id: str = "") -> Session:
        """Get the current session or create one if none exists.
        
        Args:
            agent_id: Agent ID to use if creating new session.
            
        Returns:
            The current or new Session.
        """
        with self._session_lock:
            if self._current_session is None:
                self._current_session = Session(
                    session_id=uuid.uuid4().hex[:16],
                    agent_id=agent_id or "auto",
                    started_at=datetime.now(timezone.utc),
                )
            return self._current_session
    
    def record_tool_call(self) -> Optional[str]:
        """Record a tool call in the current session.
        
        Returns:
            The session ID if a session is active.
        """
        with self._session_lock:
            if self._current_session:
                self._current_session.record_tool_call()
                return self._current_session.session_id
            return None
    
    def get_session_id(self) -> Optional[str]:
        """Get the current session ID.
        
        Returns:
            Session ID or None if no session.
        """
        with self._session_lock:
            if self._current_session:
                return self._current_session.session_id
            return None
    
    def end_session(self) -> Optional[Session]:
        """End the current session.
        
        Returns:
            The ended Session or None.
        """
        with self._session_lock:
            session = self._current_session
            self._current_session = None
            return session
    
    def get_session_info(self) -> dict:
        """Get information about the current session.
        
        Returns:
            Dictionary with session info or empty state.
        """
        with self._session_lock:
            if self._current_session:
                return self._current_session.to_dict()
            return {
                "session_id": None,
                "active": False,
                "message": "No active session. Call start_session() to begin.",
            }


# Global singleton accessor
def get_session_manager() -> SessionManager:
    """Get the global SessionManager instance."""
    return SessionManager()
