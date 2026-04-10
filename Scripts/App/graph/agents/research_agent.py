
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from google.api_core.exceptions import InternalServerError, ResourceExhausted
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from typing import Literal
from rich import print
import os

# Config imports for centralized settings
from Scripts.App.config import (
    MODEL_CONFIG,
    get_api_key,
)

from Scripts.App.graph.state.prompts import (
                                        web_research_agent_prompt,
                                        compress_research_system_prompt, 
                                        db_research_agent_prompt)
from Scripts.App.graph.state.graph_state import ResearcherState
from Scripts.App.database.database import RetrievalTool
from Scripts.App.tools.adk_db_search import database_search_tool, set_database
from Scripts.App.tools.web_search_tool import get_rotational_model_client
from Scripts.App.tools.adk_web_research import web_search_tool

from langchain_core.tools import tool
import dotenv
dotenv.load_dotenv()



@tool
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making."""
    print("\n"+"="*13+"Model Decisions"+"="*13+"\n")
    print(reflection)
    print("="*30)

    return f"Reflection recorded: {reflection}"

class ResearchAgentGraph:
    """A graph-based agent for conducting research using various tools and models."""
    def __init__(self, db_tools: RetrievalTool = None):
        if db_tools is None:
            raise ValueError("A RetrievalTool instance must be provided to proceed.")
        self.db_tools = db_tools
        set_database(self.db_tools)
        # Use centralized config for model and API key
        self.compress_model = ChatGoogleGenerativeAI(
            model=MODEL_CONFIG.medium_models[0],
            temperature=0,
            timeout=MODEL_CONFIG.llm_timeout,
            google_api_key=get_api_key("compression")
        )
        

        # Define tools and bind them to the LLM
        self.tools = [web_search_tool, think_tool, database_search_tool]
        #llm_with_tools = llm.bind_tools(tools)
        self.tools_by_name = {t.name: t for t in self.tools}

    # --- Agent Nodes ---

    def llm_call(self,state: ResearcherState):
        """The main reasoning node of the agent."""
        tools_to_use=None
        max_attempts = 3  # Number of models to try

        for attempt in range(max_attempts):
            try:
                llm = get_rotational_model_client(is_research_agent=True)
                if state.is_research_web:
                    print(f"Calling web research agent with model: {llm}")
                    tools_to_use = self.tools[:2]
                    system_prompt = web_research_agent_prompt.format(
                        date=__import__('datetime').datetime.now().strftime('%Y-%m-%d'),
                        research_topic=state.research_topic,
                        citation_style="harvard"
                    )
                else:
                    print(f"Calling database research agent with model: {llm}")
                    tools_to_use = self.tools
                    system_prompt = db_research_agent_prompt.format(
                        date=__import__('datetime').datetime.now().strftime('%Y-%m-%d'),
                        research_topic=state.research_topic,
                        citation_style="harvard"
                    )

                if not tools_to_use:
                    print("No tools provided, skipping the research.")
                    return {"messages": [ToolMessage(content="No tools provided to the agent, skipping this research")]}

                llm_with_tools = llm.bind_tools(tools_to_use)
                messages = [SystemMessage(content=system_prompt)] + state.messages
                response = llm_with_tools.invoke(messages)
                return {
                    "messages": [response],
                    "llm_turn_count": state.llm_turn_count + 1,
                }

            except (InternalServerError, ResourceExhausted) as e:
                print(f"Attempt {attempt + 1}/{max_attempts} failed with {type(e).__name__}: {e}")
                if attempt < max_attempts - 1:
                    print("Switching to the next model...")
                    continue
                else:
                    print("All model attempts failed.")
                    return {
                        "messages": [AIMessage(content=f"All model attempts failed. Last error: {e}")],
                        "llm_turn_count": state.llm_turn_count + 1,
                    }
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                return {
                    "messages": [AIMessage(content=f"An unexpected error occurred: {e}")],
                    "llm_turn_count": state.llm_turn_count + 1,
                }

        return {
            "messages": [AIMessage(content="Failed to get a response from any model.")],
            "llm_turn_count": state.llm_turn_count + 1,
        }

    async def tool_node(self, state: ResearcherState):
        """Executes the tools called by the LLM."""
        last_message = state.messages[-1]
        tool_calls = last_message.tool_calls

        # Asynchronously execute all tool calls
        import asyncio

        async def run_tool(tool_call):
            tool_name = tool_call["name"]
            call_id = tool_call.get("id") or tool_call.get("tool_call_id") or "missing_tool_call_id"
            # Handle potential tool name mismatch
            if tool_name == "web_search" or tool_name == "search":
                tool_name = "web_search_tool"
            tool_to_use = self.tools_by_name[tool_name]
            print(f"≈≈≈≈≈≈≈≈Tool called:{tool_call['name']}≈≈≈≈≈≈")
            # web_search_tool is async, think_tool is sync
            if asyncio.iscoroutinefunction(tool_to_use.ainvoke):
                return ToolMessage(
                    await tool_to_use.ainvoke(tool_call["args"]), tool_call_id=call_id
                )
            else:
                return ToolMessage(
                    tool_to_use.invoke(tool_call["args"]), tool_call_id=call_id
                )

        tool_messages = await asyncio.gather(*[run_tool(tc) for tc in tool_calls])
        new_web_errors = sum(
            1 for msg in tool_messages
            if isinstance(msg, ToolMessage) and str(msg.content).startswith("WEB_SEARCH_TOOL_ERROR")
        )
        return {
            "messages": tool_messages,
            "web_tool_error_count": state.web_tool_error_count + new_web_errors,
        }

    def compress_research(self, state: ResearcherState):
        """Compresses all research findings into a final report."""
        
        system_prompt = compress_research_system_prompt.format(
            date=__import__('datetime').datetime.now().strftime('%Y-%m-%d'),
            research_topic=state.research_topic,
            citation_style="harvard",
           
        )
        # Filter out system messages and include Human/AI/Tool messages
        compression_messages = [SystemMessage(content=system_prompt)] + [
            m for m in state.messages if isinstance(m, (HumanMessage, ToolMessage))
        ]
        print("the Compression prompt using compression model: gemini-2.5-flash")
        #print(compression_messages)

        response = self.compress_model.invoke(compression_messages)

        return {
            "messages": [response],
            "compressed_research": response.content
        }


    def should_continue(self,state: ResearcherState) -> Literal["tool_node", "__end__"]:
        """Routing logic to decide whether to continue or end."""
        last_message = state.messages[-1]
        if state.llm_turn_count >= 6:
            print("Researcher max LLM turns reached. Ending this research task.")
            return "__end__"
        if state.web_tool_error_count >= 2:
            print("Researcher encountered repeated web tool errors. Ending this research task.")
            return "__end__"
        if last_message.tool_calls:
            return "tool_node"
        return "__end__"
    
    def build(self):
        # --- Build the Graph ---

        builder = StateGraph(ResearcherState)

        builder.add_node("llm_call", self.llm_call)
        builder.add_node("tool_node", self.tool_node)
        builder.add_node("compress_research", self.compress_research)

        builder.add_edge(START, "llm_call")
        builder.add_conditional_edges(
            "llm_call",
            self.should_continue,
            {"tool_node": "tool_node", "__end__": "compress_research"}
        )
        builder.add_edge("tool_node", "llm_call")
        builder.add_edge("compress_research", END)

        researcher_agent_graph = builder.compile()
        return researcher_agent_graph

    
    