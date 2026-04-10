
import asyncio
from typing import Literal
from google.api_core.exceptions import InternalServerError, ResourceExhausted
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END

# Config imports for centralized settings
from Scripts.App.config import MODEL_CONFIG, run_with_timeout

from Scripts.App.graph.agents.research_agent import ResearchAgentGraph, think_tool, get_rotational_model_client
from Scripts.App.graph.state.graph_state import SupervisorState, ConductResearch, ResearchComplete
from Scripts.App.graph.state.prompts import supervisor_prompt
from Scripts.App.database.database import RetrievalTool

from rich import print
class SupervisorAgentGraph:
    """A graph-based agent for supervising research tasks and delegating to a worker agent."""
    def __init__(self, db_tools: RetrievalTool = None):
        # --- Supervisor Model and Tools ---
        self.supervisor_tools = [ConductResearch, ResearchComplete, think_tool]
        self.researcher_agent_graph = ResearchAgentGraph(db_tools).build()
        self.max_supervisor_turns = 8
        self.max_no_tool_turns = 3

    # --- Supervisor Agent Nodes ---

    def supervisor_node(self, state: SupervisorState):
        """The main reasoning node for the supervisor."""
        max_attempts = 3  # Number of models to try

        for attempt in range(max_attempts):
            try:
                # Get a new model on each attempt
                supervisor_model = get_rotational_model_client(is_supervisor=True)
                supervisor_llm_with_tools = supervisor_model.bind_tools(self.supervisor_tools)

                system_prompt = SystemMessage(content=supervisor_prompt.format(
                    date=__import__('datetime').datetime.now().strftime('%Y-%m-%d'),
                    research_brief=state.research_brief
                ))
                messages = [system_prompt] + state.messages
                print(f"\nSupervisor prompt for model {supervisor_model}\n")
                
                response = supervisor_llm_with_tools.invoke(messages)
                print("Got response")
                no_tool_turns = 0 if response.tool_calls else state.no_tool_turn_count + 1
                return {
                    "messages": [response],
                    "supervisor_turn_count": state.supervisor_turn_count + 1,
                    "no_tool_turn_count": no_tool_turns,
                }

            except (InternalServerError, ResourceExhausted) as e:
                print(f"Supervisor attempt {attempt + 1}/{max_attempts} failed with {type(e).__name__}: {e}")
                if attempt < max_attempts - 1:
                    print("Switching to the next model for supervisor...")
                    continue
                else:
                    print("All supervisor model attempts failed.")
                    return {
                        "messages": [AIMessage(content=f"All supervisor model attempts failed. Last error: {e}")],
                        "supervisor_turn_count": state.supervisor_turn_count + 1,
                        "no_tool_turn_count": state.no_tool_turn_count + 1,
                    }
            except Exception as e:
                print(f"An unexpected error occurred in supervisor: {e}")
                return {
                    "messages": [AIMessage(content=f"An unexpected error occurred in supervisor: {e}")],
                    "supervisor_turn_count": state.supervisor_turn_count + 1,
                    "no_tool_turn_count": state.no_tool_turn_count + 1,
                }

    async def supervisor_tool_node(self, state: SupervisorState):
        """
        Executes tools called by the supervisor.
        This is where delegation to the worker agent happens.
        """
        last_message = state.messages[-1]
        tool_calls = last_message.tool_calls

        # Separate tool calls for concurrent and sequential execution
        conduct_research_calls = [tc for tc in tool_calls if tc['name'] == 'ConductResearch']
        other_calls = [tc for tc in tool_calls if tc['name'] != 'ConductResearch']

        tool_messages = []
        notes = state.notes or []

        # Enforce single-worker mode: only run one ConductResearch task per turn.
        if conduct_research_calls:
            tool_call = conduct_research_calls[0]
            call_id = tool_call.get('id') or tool_call.get('tool_call_id') or 'missing_tool_call_id'
            result_state = await self.researcher_agent_graph.ainvoke({
                "research_topic": tool_call['args']['research_topic'],
                # Pass the research_topic as a HumanMessage to the worker agent
                "messages": [HumanMessage(content=tool_call['args']['research_topic'])],
                "is_research_web":state.is_research_web
            })
            compressed = result_state.get('compressed_research', '')
            tool_messages.append(ToolMessage(
                content=compressed,
                tool_call_id=call_id
            ))
            notes.append(compressed)

            if len(conduct_research_calls) > 1:
                skipped = len(conduct_research_calls) - 1
                skipped_call_id = conduct_research_calls[-1].get('id') or conduct_research_calls[-1].get('tool_call_id') or 'missing_tool_call_id'
                tool_messages.append(ToolMessage(
                    content=f"Skipped {skipped} extra ConductResearch call(s) to enforce single-worker mode.",
                    tool_call_id=skipped_call_id
                ))

        # Execute other tools sequentially (e.g., think_tool)
        for tool_call in other_calls:
            if tool_call['name'] == 'think_tool':
                result = think_tool.invoke(tool_call['args'])
                call_id = tool_call.get('id') or tool_call.get('tool_call_id') or 'missing_tool_call_id'
                tool_messages.append(ToolMessage(content=result, tool_call_id=call_id))

        return {
            "messages": tool_messages,
            "notes": notes,
            "is_research_web": state.is_research_web,
            "no_tool_turn_count": 0,
        }


    def route_supervisor(self, state: SupervisorState) -> Literal["supervisor", "supervisor_tool_node", "__end__"]:
        """Routing logic for the supervisor."""
        last_message = state.messages[-1]

        # Guardrail against provider/model loops where no tool calls are emitted.
        if state.supervisor_turn_count >= self.max_supervisor_turns:
            print(f"Max supervisor turns reached ({self.max_supervisor_turns}). Ending supervision loop.")
            return END

        if not last_message.tool_calls:
            if state.no_tool_turn_count >= self.max_no_tool_turns:
                print(
                    f"Supervisor produced no tool calls for {state.no_tool_turn_count} consecutive turns. Ending supervision loop."
                )
                return END
            # If there are no tool calls, loop back to the supervisor to continue the process
            return "supervisor"

        if any(tc['name'] == 'ResearchComplete' for tc in last_message.tool_calls):
            # If ResearchComplete is called, end the process
            return END
        # Otherwise, execute the requested tools
        return "supervisor_tool_node"

    def build(self):
        # --- Build the Supervisor Graph ---

        builder = StateGraph(SupervisorState)

        builder.add_node("supervisor", self.supervisor_node)
        builder.add_node("supervisor_tool_node", self.supervisor_tool_node)

        builder.add_edge(START, "supervisor")
        builder.add_conditional_edges(
            "supervisor",
            self.route_supervisor,
            {"supervisor_tool_node": "supervisor_tool_node", "supervisor": "supervisor", END: END}
        )
        builder.add_edge("supervisor_tool_node", "supervisor")

        supervisor_agent_graph = builder.compile()
        return supervisor_agent_graph