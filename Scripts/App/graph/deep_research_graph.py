import sys
import os
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from rich import print
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv

from Scripts.App.graph.state.graph_state import AgentState
from Scripts.App.graph.state.deep_prompts import deep_analysis_prompt, deep_report_generation_prompt
from Scripts.App.graph.agents.clarification_agent import ClarificationAgentGraph
from Scripts.App.graph.agents.supervisor_agent import SupervisorAgentGraph
from Scripts.App.graph.state.graph_state import SupervisorState
from Scripts.App.database.database import RetrievalTool

load_dotenv()

class DeepResearchGraph:
    """
    A specialized graph for 'Deep Research' that includes thematic analysis,
    gap identification, and source verification.
    """
    def __init__(self, db_tools: RetrievalTool = None):
        self.scoping_agent = ClarificationAgentGraph().build()
        self.supervisor_agent = SupervisorAgentGraph(db_tools).build()

    # --- Nodes ---

    def start_scoping(self, state: AgentState):
        """Reuses the existing scoping agent."""
        print("[bold blue]--- Step 1: Scoping & Clarification ---[/bold blue]")
        scoping_result = self.scoping_agent.invoke(state)
        return {
            "messages": scoping_result.get("messages", []),
            "research_brief": scoping_result.get("research_brief", ""),
            "is_research_web": state.is_research_web
        }

    async def start_broad_research(self, state: AgentState):
        """Reuses the supervisor agent for broad data gathering."""
        print("[bold blue]--- Step 2: Broad Research (Data Gathering) ---[/bold blue]")
        research_brief = state.research_brief
        supervisor_initial_state = SupervisorState(
            research_brief=research_brief,
            messages=[m for m in state.messages if isinstance(m, HumanMessage)],
            is_research_web=state.is_research_web
        )
        
        try:
            supervisor_result = await self.supervisor_agent.ainvoke(supervisor_initial_state)
        except ResourceExhausted as e:
            print(f"[bold red]Fatal Error:[/bold red] API Rate limit exceeded during research. {e}")
            sys.exit(1)

        existing_notes = state.notes or []
        return {
            "notes": existing_notes + supervisor_result.get('notes', []),
            "research_brief": research_brief,
            "is_research_web": state.is_research_web
        }

    def perform_deep_analysis(self, state: AgentState):
        """
        New Node: Analyzes the gathered notes for themes, gaps, and source credibility.
        """
        print("[bold blue]--- Step 3: Deep Analysis (Themes, Gaps, Verification) ---[/bold blue]")
        notes_str = "\n\n".join(state.notes)
        prompt = deep_analysis_prompt.format(
            research_brief=state.research_brief,
            notes=notes_str
        )
        
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        try:
            response = model.invoke([HumanMessage(content=prompt)])
            deep_analysis_summary = response.content
            print("[green]Deep Analysis Complete.[/green]")
            return {"deep_analysis_summary": deep_analysis_summary}
        except Exception as e:
            print(f"[red]Error during Deep Analysis: {e}[/red]")
            return {"deep_analysis_summary": "Deep analysis failed due to an error."}

    def generate_deep_report(self, state: AgentState):
        """
        New Node: Generates the comprehensive Deep Research Report.
        """
        print("[bold blue]--- Step 4: Generating Deep Research Report ---[/bold blue]")
        notes_str = "\n\n".join(state.notes)
        
        # Use the deep analysis summary if available, otherwise fallback
        deep_analysis = state.get("deep_analysis_summary", "No deep analysis available.")

        prompt = deep_report_generation_prompt.format(
            date=__import__('datetime').datetime.now().strftime('%Y-%m-%d'),
            research_brief=state.research_brief,
            deep_analysis=deep_analysis,
            notes=notes_str,
            citation_style="harvard"
        )

        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        try:
            response = model.invoke([HumanMessage(content=prompt)])
            final_report = response.content
            return {
                "final_report": final_report,
                "messages": [HumanMessage(content=final_report)]
            }
        except Exception as e:
            print(f"[red]Error generating report: {e}[/red]")
            return {"final_report": "Failed to generate report."}

    def build(self):
        builder = StateGraph(AgentState)
        
        builder.add_node("scoping", self.start_scoping)
        builder.add_node("broad_research", self.start_broad_research)
        builder.add_node("deep_analysis", self.perform_deep_analysis)
        builder.add_node("generate_deep_report", self.generate_deep_report)

        builder.add_edge(START, "scoping")
        builder.add_edge("scoping", "broad_research")
        builder.add_edge("broad_research", "deep_analysis")
        builder.add_edge("deep_analysis", "generate_deep_report")
        builder.add_edge("generate_deep_report", END)

        return builder.compile()
