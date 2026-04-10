

from typing import List, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
import operator
from langgraph.graph.message import add_messages
from typing_extensions import Annotated

# The Pydantic model for our agent's state.
class ResearcherState(BaseModel):
    """
    Represents the state of our research agent.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]= Field(
        ...,
        description="The conversation history of the agent."
    )
    research_topic: str = Field(
        ...,
        description="The specific topic the agent is currently researching."
    )
    # The final compressed research report
    compressed_research: str = Field(
        default="",
        description="A compressed summary of all research findings."
    )
    # All raw notes and summaries from tool calls
    raw_notes: List[str] = Field(
        default_factory=list,
        description="Raw notes and content gathered from tool calls."
    )

    is_research_web: bool = Field(
    default=True,
    description="Decides weather to use only web search tool only or the local database"
    )
    llm_turn_count: int = Field(
        default=0,
        description="Count of LLM reasoning turns within the researcher graph."
    )
    web_tool_error_count: int = Field(
        default=0,
        description="Count of web tool errors encountered in this researcher run."
    )



# --- Pydantic Models for Structured Output ---

class ClarifyWithUser(BaseModel):
    """Schema for user clarification decision and questions."""
    need_clarification: bool = Field(
        description="Whether the user needs to be asked a clarifying question.",
    )
    question: str = Field(
        description="A concise question to ask the user to clarify the report scope. Only ask if clarification is needed.",
        default=""
    )
    verification_message: str = Field(
        description="A message to the user confirming we will start research. Only use if no clarification is needed.",
        default=""
    )
    is_research_web: bool = Field(
    default=True,
    description="Decides weather to use only web search tool only or the local database"
    )

class ResearchBrief(BaseModel):
    """Schema for a structured research brief."""
    research_brief: str = Field(
        description="A detailed, comprehensive research brief generated from the conversation history.",
    )
    is_research_web: bool = Field(
    default=True,
    description="Decides weather to use only web search tool only or the local database"
    )

# --- State Definitions ---

class AgentState(BaseModel):
    """
    Main state for the full multi-agent research system.
    This will be the shared state across all graphs.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages] = Field(
        ...,
        description="The conversation history."
    )
    research_brief: str = Field(
        default="",
        description="The detailed research brief that guides the overall research direction."
    )
    # This field will eventually hold the final report
    final_report: str = Field(
        default="",
        description="The final, formatted research report."
    )
    # A list of research notes aggregated from all sub-agents
    notes: List[str] = Field(
        default_factory=list,
        description="A list of research notes aggregated from all sub-agents."
    )
    is_research_web: bool = Field(
    default=True,
    description="Decides weather to use only web search tool only or the local database"
    )



class SupervisorState(BaseModel):
    """
    State for the multi-agent research supervisor.
    Manages coordination between supervisor and research agents.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]= Field(
        ...,
        description="The conversation history of the agent."
    )
    research_brief: str = Field(
        ...,
        description="The detailed research brief that guides the overall research direction."
    )
    # A list of research notes aggregated from all sub-agents
    notes: List[str] = Field(
        default_factory=list,
        description="A list of research notes aggregated from all sub-agents."
    )
    is_research_web: bool = Field(
    default=True,
    description="Decides weather to use only web search tool only or the local database"
    )
    supervisor_turn_count: int = Field(
        default=0,
        description="Count of supervisor reasoning turns to enforce termination limits."
    )
    no_tool_turn_count: int = Field(
        default=0,
        description="Count of consecutive supervisor turns with no tool calls."
    )

class ConductResearch(BaseModel):
    """
    Tool for delegating a research task to a specialized sub-agent.
    """
    research_topic: str = Field(
        description="A clear and specific research topic for the sub-agent. Should be a self-contained task."
    )

class ResearchComplete(BaseModel):
    """
    Tool for indicating that the research process is complete and all necessary information has been gathered.
    """
    pass