
from langgraph.graph import StateGraph, START, END
import os
import asyncio
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from rich import print
from google.api_core.exceptions import ResourceExhausted

# Config imports for centralized settings
from Scripts.App.config import MODEL_CONFIG, get_api_key

# Utilities
from Scripts.App.utils import get_research_logger

from Scripts.App.graph.state.graph_state import AgentState
from Scripts.App.graph.state.prompts import final_report_generation_prompt
from Scripts.App.graph.agents.clarification_agent import ClarificationAgentGraph
from Scripts.App.graph.agents.supervisor_agent import SupervisorAgentGraph
from Scripts.App.graph.state.graph_state import SupervisorState
from Scripts.App.database.database import RetrievalTool
from Scripts.App.tools.adk_web_research import web_search_tool
from dotenv import load_dotenv
load_dotenv()

class NeetResearchAppGraph:
    """The main graph-based application for conducting structured research."""
    def __init__(self, db_tools: RetrievalTool = None):
        self.scoping_agent = ClarificationAgentGraph().build()
        self.supervisor_agent = SupervisorAgentGraph(db_tools).build()
    # --- Main Graph Nodes ---

    def start_scoping(self, state: AgentState):
        """
        Invokes the scoping agent to clarify and generate a research brief.
        This is the entry point for the user interaction part.
        """
        scoping_result = self.scoping_agent.invoke(state)
        print(f'After scoping, web: {scoping_result.get("is_research_web")}')
        return {"messages": scoping_result.get("messages", []), "research_brief": scoping_result.get("research_brief", ""), "is_research_web":state.is_research_web}

    async def start_supervision(self, state: AgentState):
        """
        Invokes the supervisor agent to conduct the research.
        This node receives the research_brief from the scoping phase.
        """
        logger = get_research_logger()
        start_time = time.time()
        logger.phase_start("Research Supervision")
        
        research_brief = state.research_brief
        supervisor_initial_state = SupervisorState(
            research_brief=research_brief,
            # Pass the existing HumanMessage from the main state to the supervisor
            messages=[m for m in state.messages if isinstance(m, HumanMessage)],
            is_research_web=state.is_research_web
        )
        try:
            # Add timeout wrapper to prevent hanging
            supervisor_result = await asyncio.wait_for(
                self.supervisor_agent.ainvoke(supervisor_initial_state),
                timeout=MODEL_CONFIG.session_timeout  # 1 hour max
            )
        except asyncio.TimeoutError:
            print("\n--- RESEARCH TIMEOUT ---")
            print(f"Research timed out after {MODEL_CONFIG.session_timeout} seconds.")
            raise RuntimeError(
                f"Research timed out after {MODEL_CONFIG.session_timeout} seconds without completion."
            )
        except ResourceExhausted as e:
            print(f"\n--- FATAL RESEARCH ERROR ---" )
            print("A 'ResourceExhausted' error occurred during the research phase.")
            print("This usually means you have hit your API rate limits.")
            print(f"Error details: {e}")
            raise RuntimeError(f"Research failed due to API rate limits: {e}")


        # Return both the notes and the research brief forward
        # Accumulate notes from the supervisor's result
        existing_notes = state.notes or []
        return {
            "notes": existing_notes + supervisor_result.get('notes', []),
            "research_brief": research_brief,
            "is_research_web": state.is_research_web
        }


    async def generate_final_report(self,state: AgentState):
        """
        Generates the final, polished research report from the supervisor's notes.
        """
        usable_notes = [
            n for n in (state.notes or [])
            if isinstance(n, str)
            and n.strip()
            and "WEB_SEARCH_TOOL_ERROR" not in n
            and ("--- SOURCE" in n or "REFERENCE:" in n)
        ]
        if not usable_notes:
            # Resilience fallback: perform one direct web retrieval from the brief.
            fallback_candidates = []
            if state.messages:
                first_msg_content = getattr(state.messages[0], "content", "")
                if isinstance(first_msg_content, str) and first_msg_content.strip():
                    fallback_candidates.append(first_msg_content.strip())
            if state.research_brief and state.research_brief.strip():
                fallback_candidates.append(state.research_brief.strip())

            for fallback_query in fallback_candidates:
                fallback_result = await web_search_tool.ainvoke({"query": fallback_query})
                if isinstance(fallback_result, str) and "--- SOURCE" in fallback_result:
                    usable_notes = [fallback_result]
                    break

        if not usable_notes:
            raise ValueError("No usable web research notes were produced. Aborting final report generation.")

        notes_str = "\n\n".join(usable_notes)

        research_brief = state.research_brief
        prompt = final_report_generation_prompt.format(
            date=__import__('datetime').datetime.now().strftime('%Y-%m-%d'),
            research_brief=research_brief,
            notes=notes_str,
            citation_style="harvard"
        )
        print("================================= Final report ==========================")
        print(prompt)
        print("Generating Final Report...")
        print("============================================================================")

        # Use centralized config for models
        report_generation_models = MODEL_CONFIG.complex_models
        final_report_content = None

        for model_name in report_generation_models:
            try:
                print(f"Attempting to generate report with model: {model_name}")
                model = ChatGoogleGenerativeAI(
                    model=model_name, 
                    temperature=0, 
                    timeout=MODEL_CONFIG.llm_timeout,
                    google_api_key=get_api_key("report")
                )
                response = model.invoke([HumanMessage(content=prompt)])
                final_report_content = response.content
                print(f"Successfully generated report with {model_name}")
                break  # Exit loop on success
            except ResourceExhausted as e:
                print(f"Model {model_name} is rate-limited. Trying next model. Error: {e}", style="yellow")
                continue # Move to the next model

        if final_report_content is None:
            print("All report generation models failed due to rate limiting.")
            print("Saving the final report prompt to 'output/partials/final_report_prompt.txt'.")
            with open("./output/partials/final_report_prompt.txt", "w", encoding="utf-8") as f:
                f.write(prompt)
            final_report_content = "Failed to generate report due to API errors. The prompt has been saved to 'output/partials/final_report_prompt.txt'."

        return {
            "final_report": final_report_content,
            "messages": [HumanMessage(content=final_report_content)],
            "is_research_web": state.is_research_web
        }

    def build(self):
        # --- Build the Main Graph ---

        builder = StateGraph(AgentState)
        # Define the nodes of the master workflow
        builder.add_node("scoping", self.start_scoping)
        builder.add_node("supervision", self.start_supervision)
        builder.add_node("generate_report", self.generate_final_report)
        # Nodes connections
        builder.add_edge(START, "scoping")
        builder.add_edge("scoping", "supervision")
        builder.add_edge("supervision", "generate_report")
        builder.add_edge("generate_report", END)
        # Compile the graph
        neet_research_app = builder.compile()
        return neet_research_app