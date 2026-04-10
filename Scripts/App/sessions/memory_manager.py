"""
Memory Manager for NeetResearch App.

Provides rolling summarization to prevent context overflow
during long research sessions.
"""

from typing import Dict, List, Optional
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from Scripts.App.config import MODEL_CONFIG, get_api_key


class RollingMemory:
    """
    Manages message history with summarization to prevent overflow.
    
    When messages exceed max_messages, older messages are summarized
    and compressed into a context summary.
    """
    
    def __init__(
        self, 
        max_messages: int = None,
        summarizer = None
    ):
        """
        Initialize rolling memory.
        
        Args:
            max_messages: Maximum messages before summarization
            summarizer: LLM for summarization (auto-created if None)
        """
        self.max_messages = max_messages or MODEL_CONFIG.max_messages
        self.summarizer = summarizer
        self.running_summary = ""
        self.summaries: List[str] = []
    
    def _get_summarizer(self):
        """Get or create the summarizer LLM."""
        if self.summarizer is None:
            self.summarizer = ChatGoogleGenerativeAI(
                model=MODEL_CONFIG.simple_models[0],  # Use Flash-Lite
                temperature=0,
                timeout=MODEL_CONFIG.llm_timeout,
                google_api_key=get_api_key("summarization")
            )
        return self.summarizer
    
    def process(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Process messages, summarizing old ones if needed.
        
        Args:
            messages: Current message list
        
        Returns:
            Processed messages (possibly with summary prefix)
        """
        if len(messages) <= self.max_messages:
            return messages
        
        # Split into old and recent
        cutoff = len(messages) - self.max_messages
        old_messages = messages[:cutoff]
        recent_messages = messages[cutoff:]
        
        # Summarize old messages
        summary = self._summarize(old_messages)
        if summary:
            self.summaries.append(summary)
            # Keep only last 5 summaries to prevent unlimited growth
            self.running_summary = "\n\n---\n\n".join(self.summaries[-5:])
        
        # Build context with summary + recent
        result = []
        if self.running_summary:
            result.append(SystemMessage(
                content=f"[Previous Research Summary]\n{self.running_summary}"
            ))
        result.extend(recent_messages)
        
        print(f"📝 Compressed {len(old_messages)} messages into summary")
        return result
    
    def _summarize(self, messages: List[BaseMessage]) -> str:
        """
        Summarize a batch of messages.
        
        Args:
            messages: Messages to summarize
        
        Returns:
            Summary string
        """
        # Extract content from messages
        content_parts = []
        for m in messages:
            if hasattr(m, 'content') and m.content:
                role = "User" if isinstance(m, HumanMessage) else "Assistant"
                content_parts.append(f"[{role}]: {m.content[:5000]}")
        
        if not content_parts:
            return ""
        
        content = "\n---\n".join(content_parts)
        
        # Truncate if too long
        content = content[:50000]
        
        try:
            summarizer = self._get_summarizer()
            result = summarizer.invoke(
                f"Summarize these research findings in 500 words. "
                f"Preserve key facts, citations, and important findings:\n\n{content}"
            )
            return result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            print(f"⚠️ Summarization failed: {e}")
            return f"[Summary failed - {len(content_parts)} messages]"
    
    def get_summary(self) -> str:
        """Get the current running summary."""
        return self.running_summary
    
    def reset(self):
        """Reset the memory state."""
        self.running_summary = ""
        self.summaries = []


class MemoryManager:
    """
    Advanced memory manager with tiered storage.
    
    Implements a three-tier system:
    - Working memory: Current context (last N messages)
    - Short-term memory: Recent summaries
    - Long-term memory: Archived summaries (future: vector store)
    """
    
    def __init__(
        self,
        working_memory_size: int = 10,
        short_term_size: int = 5
    ):
        """
        Initialize memory manager.
        
        Args:
            working_memory_size: Messages in working memory
            short_term_size: Summaries in short-term memory
        """
        self.working_memory_size = working_memory_size
        self.short_term_size = short_term_size
        
        self.working_memory: List[BaseMessage] = []
        self.short_term_memory: List[str] = []
        self.long_term_memory: List[str] = []
        
        self.rolling_memory = RollingMemory(max_messages=working_memory_size)
    
    def add_message(self, message: BaseMessage):
        """
        Add a message to memory.
        
        Args:
            message: Message to add
        """
        self.working_memory.append(message)
        
        # Check if we need to compress
        if len(self.working_memory) > self.working_memory_size:
            self._compress_working_memory()
    
    def _compress_working_memory(self):
        """Compress older messages to short-term."""
        processed = self.rolling_memory.process(self.working_memory)
        
        # Extract summary if one was created
        if processed and isinstance(processed[0], SystemMessage):
            if "[Previous Research Summary]" in processed[0].content:
                summary = processed[0].content
                if summary not in self.short_term_memory:
                    self.short_term_memory.append(summary)
        
        # Keep only recent messages
        self.working_memory = [
            m for m in processed 
            if not isinstance(m, SystemMessage)
        ]
        
        # Move old summaries to long-term
        if len(self.short_term_memory) > self.short_term_size:
            self.long_term_memory.extend(
                self.short_term_memory[:-self.short_term_size]
            )
            self.short_term_memory = self.short_term_memory[-self.short_term_size:]
    
    def get_context(self) -> List[BaseMessage]:
        """
        Get current context for LLM.
        
        Returns:
            List of messages with context
        """
        result = []
        
        # Add most recent short-term summary
        if self.short_term_memory:
            result.append(SystemMessage(
                content=self.short_term_memory[-1]
            ))
        
        # Add working memory
        result.extend(self.working_memory)
        
        return result
    
    def get_full_history(self) -> Dict:
        """Get full memory state for debugging."""
        return {
            "working_memory": len(self.working_memory),
            "short_term_memory": len(self.short_term_memory),
            "long_term_memory": len(self.long_term_memory),
        }
    
    def reset(self):
        """Reset all memory."""
        self.working_memory = []
        self.short_term_memory = []
        self.long_term_memory = []
        self.rolling_memory.reset()
