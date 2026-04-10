"""
Logging Configuration for NeetResearch App.

Provides structured logging to replace print statements.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


# Custom formatter with colors for console
class ColorFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    name: str = "neetresearch",
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    Setup logging for the application.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for log output
        console: Whether to log to console
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers = []
    
    # Console handler with colors
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_format = ColorFormatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
    
    # File handler (no colors)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "neetresearch") -> logging.Logger:
    """
    Get or create a logger.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # Setup if not configured
    if not logger.handlers:
        setup_logging(name)
    
    return logger


class ResearchLogger:
    """
    Specialized logger for research operations.
    
    Provides semantic logging methods for research phases.
    """
    
    def __init__(self, session_id: str = None):
        """
        Initialize research logger.
        
        Args:
            session_id: Optional session ID for context
        """
        self.logger = get_logger("neetresearch.research")
        self.session_id = session_id or "no-session"
    
    def _prefix(self, emoji: str, msg: str) -> str:
        """Add session prefix to message."""
        return f"[{self.session_id[:8]}] {emoji} {msg}"
    
    def phase_start(self, phase: str):
        """Log start of a research phase."""
        self.logger.info(self._prefix("🚀", f"Starting phase: {phase}"))
    
    def phase_complete(self, phase: str):
        """Log completion of a research phase."""
        self.logger.info(self._prefix("✅", f"Completed phase: {phase}"))
    
    def source_found(self, source: str):
        """Log when a source is found."""
        self.logger.debug(self._prefix("📖", f"Found source: {source[:50]}..."))
    
    def llm_call(self, model: str, purpose: str):
        """Log LLM API call."""
        self.logger.debug(self._prefix("🤖", f"Calling {model} for {purpose}"))
    
    def llm_response(self, model: str, tokens: int = None):
        """Log LLM response received."""
        msg = f"Response from {model}"
        if tokens:
            msg += f" ({tokens} tokens)"
        self.logger.debug(self._prefix("📝", msg))
    
    def rate_limit_hit(self, wait_time: int):
        """Log rate limit event."""
        self.logger.warning(self._prefix("⏳", f"Rate limit hit, waiting {wait_time}s"))
    
    def error(self, msg: str, exc: Exception = None):
        """Log error."""
        if exc:
            self.logger.error(self._prefix("❌", f"{msg}: {exc}"), exc_info=True)
        else:
            self.logger.error(self._prefix("❌", msg))
    
    def warning(self, msg: str):
        """Log warning."""
        self.logger.warning(self._prefix("⚠️", msg))
    
    def info(self, msg: str):
        """Log info."""
        self.logger.info(self._prefix("ℹ️", msg))
    
    def debug(self, msg: str):
        """Log debug."""
        self.logger.debug(self._prefix("🔍", msg))
    
    def research_complete(self, sources_count: int, duration: float):
        """Log research completion."""
        self.logger.info(self._prefix(
            "🎉", 
            f"Research complete! {sources_count} sources in {duration:.1f}s"
        ))


# Global logger instance
_research_logger: Optional[ResearchLogger] = None


def get_research_logger(session_id: str = None) -> ResearchLogger:
    """Get or create research logger."""
    global _research_logger
    if _research_logger is None or (session_id and _research_logger.session_id != session_id):
        _research_logger = ResearchLogger(session_id)
    return _research_logger


# Initialize logging on import
setup_logging()
