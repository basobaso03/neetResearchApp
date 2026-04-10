import os
from google.api_core.exceptions import InternalServerError, ResourceExhausted
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from typing import Literal
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages import get_buffer_string
from rich import print

# Config imports for centralized settings
from Scripts.App.config import MODEL_CONFIG, get_api_key

from Scripts.App.graph.state.graph_state import AgentState, ClarifyWithUser, ResearchBrief
from Scripts.App.graph.state.prompts import clarify_with_user_instructions, generate_research_brief_instructions

from dotenv import load_dotenv
load_dotenv()


class ClarificationAgentGraph:
    """A graph-based agent for clarifying user queries and generating research briefs."""
    def __init__(self):
        pass

    def _invoke_structured(self, prompt: str, schema, task: str, max_attempts: int = 6):
        """Invoke structured-output model with model/key rotation across attempts."""
        models = MODEL_CONFIG.simple_models or ["gemini-2.5-flash-lite"]
        last_error = None

        for attempt in range(max_attempts):
            model_name = models[attempt % len(models)]
            try:
                model = ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=0,
                    timeout=MODEL_CONFIG.llm_timeout,
                    max_retries=0,
                    google_api_key=get_api_key(task)
                )
                structured_model = model.with_structured_output(schema)
                return structured_model.invoke(prompt)
            except (InternalServerError, ResourceExhausted) as e:
                last_error = e
                print(f"{task} attempt {attempt + 1}/{max_attempts} failed with {type(e).__name__}: {e}")
                continue
            except Exception as e:
                last_error = e
                print(f"{task} attempt {attempt + 1}/{max_attempts} unexpected error: {e}")
                continue

        raise RuntimeError(f"Failed to complete {task} after {max_attempts} attempts: {last_error}")

    # --- Scoping Agent Nodes ---

    def clarify_with_user(self,state: AgentState):
        """
        Determines if clarification is needed from the user.
        """
        prompt = clarify_with_user_instructions.format(
            date=__import__('datetime').datetime.now().strftime('%Y-%m-%d'),
            messages=get_buffer_string(state.messages)
        )
        print("Clarifying the question with the user")
        response: ClarifyWithUser = self._invoke_structured(
            prompt=prompt,
            schema=ClarifyWithUser,
            task="clarification",
        )

        if response.need_clarification:
            # Ask the clarifying question
            return {"messages": [AIMessage(content=response.question)]}
        else:
            # Confirm and proceed
            return {"messages": [AIMessage(content=response.verification_message)]}

    def generate_research_brief(self,state: AgentState):
        """
        Generates the detailed research brief from the conversation.
        """
        print("=====================Agent Notification===================")
        print(state.messages[-1].content)
        print("==========================================================")
        prompt = generate_research_brief_instructions.format(
            date=__import__('datetime').datetime.now().strftime('%Y-%m-%d'),
            messages=get_buffer_string(state.messages)
        )
        print("Generating Research Brief")
        response: ResearchBrief = self._invoke_structured(
            prompt=prompt,
            schema=ResearchBrief,
            task="scoping",
        )
        print("=====≈============================Research Brief=======================")
        print(response.research_brief)
        print(f"Is web_search used: {state.is_research_web}")
        print("========================================================================")
        return {"research_brief": response.research_brief,
                "is_research_web":state.is_research_web}


    def ask_user_input(self, state:AgentState):
        print("="*25)
        print("There is need for clarification here")
        print(f"Agent Question:{state.messages[-1]}")
        user_response = input("Your Response:  ")
        return {"messages": [HumanMessage(content=user_response)]}


    def route_clarification(self, state: AgentState) -> Literal["generate_research_brief", "__end__"]:
        """
        Routing logic. If the last message is from the AI asking a question,
        we end the current run and wait for user input. Otherwise, we proceed.
        """
        last_message = state.messages[-1]
        interactive_mode = os.getenv("NEET_INTERACTIVE_CLARIFICATION", "0") == "1"
        # If the AI just asked a question, we need to wait for the user's answer
        if interactive_mode and isinstance(last_message, AIMessage) and last_message.content.endswith('?'):
            return "clarify"
        # Otherwise, we have enough info to generate the brief
        return "generate_research_brief"

    def build(self):
            # --- Build the Graph ---

        builder = StateGraph(AgentState)

        builder.add_node("clarify_with_user", self.clarify_with_user)
        builder.add_node("generate_research_brief", self.generate_research_brief)
        builder.add_node("clarify", self.ask_user_input)

        builder.add_edge(START, "clarify_with_user")
        builder.add_conditional_edges(
            "clarify_with_user",
            self.route_clarification,
            {"generate_research_brief": "generate_research_brief", "clarify": "clarify"}

        )
        builder.add_edge("clarify","clarify_with_user")
        builder.add_edge("generate_research_brief", END)

        return builder.compile()