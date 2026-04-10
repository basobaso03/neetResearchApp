# ==============================================================================
#  Google ADK-Powered Research Agent
#
#  This script implements a research agent using the Google AI Developer Kit (ADK).
#  It replaces a manual web scraping implementation with the ADK's native
#  `google_search` tool for simplicity and robustness.
# ==============================================================================

import os
import asyncio
import itertools
import uuid
from typing import List
import time
import traceback
import json
import re

# --- ADK & Google Imports ---
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types as genai_types
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.tools import tool

# --- Utility Imports ---
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from rich import print

# --- Config Import (centralized settings) ---
from Scripts.App.config import MODEL_CONFIG, get_api_key

# --- Cache Import ---
from Scripts.App.utils import get_search_cache, get_research_logger

# Load environment variables from .env file
load_dotenv()


# --- Model Pool for High-Frequency Tasks ---
# Use centralized config for models
ROTATIONAL_MODELS = MODEL_CONFIG.research_models

# Create an iterator that cycles through the models indefinitely for load balancing.
model_cycler = itertools.cycle(ROTATIONAL_MODELS)

# make model_name global
model_name = None


def get_rotational_model_client(is_supervisor=False, is_research_agent=False, temperature=0.0, max_retries=3):
    """
    Returns a ChatGoogleGenerativeAI client with the next model from the
    rotational pool. This function is HEAVILY USED by other modules and is
    preserved in its original form.
    """
    print("Waiting for 6 seconds to get your next model....")

    supervisor_models = MODEL_CONFIG.supervisor_models
    time.sleep(6)  # A delay to respect API rate limits
    model_name = next(model_cycler)

    if is_supervisor:
        while model_name not in supervisor_models:
            model_name = next(model_cycler)

    print(f"--- Done waiting. Your next model is: [bold green]{model_name}[/bold green] ---")
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_retries=max_retries,
        timeout=MODEL_CONFIG.llm_timeout,
        google_api_key=get_api_key("research")
    )


# --- Pydantic Schemas for Structured Output ---

class SummarySchema(BaseModel):
    """Represents a summary and key excerpts of content for citation."""
    title: str = Field(..., description="The title of the article or page.")
    source_name: str = Field(..., description="The name of the website or source (e.g., 'Wikipedia', 'New York Times').")
    summary: str = Field(..., description="A concise summary of the content relevant to the user's query.")
    key_excerpts: str = Field(..., description="Key quotes, excerpts, examples or illustrations that directly address the user's query.")
    references: str = Field(..., description="references from the source document, specifically the URL, to be used for citation.")


class FinalReport(BaseModel):
    """A final report containing summaries of all relevant web search results."""
    report: List[SummarySchema] = Field(..., description="A list of summaries from processed web pages.")


def _extract_json_payload(text: str) -> str:
    """Extract the largest JSON object from model output text."""
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start:end + 1]
    return cleaned


def _extract_text_from_event(event) -> str:
    """Safely concatenate all text parts from an ADK event."""
    if not event or not getattr(event, "content", None):
        return ""
    parts = getattr(event.content, "parts", None) or []
    text_chunks = []
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            text_chunks.append(text)
    return "\n".join(text_chunks).strip()


def _compact_text(value: str) -> str:
    """Normalize whitespace for cleaner agent-facing tool output."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _normalize_report_items(items: List[SummarySchema]) -> List[SummarySchema]:
    """Normalize and deduplicate report items by reference URL."""
    normalized = []
    seen_refs = set()

    for item in items:
        normalized_item = SummarySchema(
            title=_compact_text(item.title),
            source_name=_compact_text(item.source_name),
            summary=_compact_text(item.summary),
            key_excerpts=_compact_text(item.key_excerpts),
            references=_compact_text(item.references),
        )

        # Keep only well-formed entries with source identity for clear citations.
        if not normalized_item.title or not normalized_item.references:
            continue

        ref_key = normalized_item.references.lower()
        if ref_key in seen_refs:
            continue
        seen_refs.add(ref_key)
        normalized.append(normalized_item)

    return normalized


# --- ADK Agent Factory ---

def create_dynamic_research_agent(query: str) -> LlmAgent:
    """
    Creates and returns a new ADK research agent instance using a model
    from the rotational pool. This ensures each search task can use a
    different, dynamically selected model.
    """
    # 1. Get the next model client from the existing rotational function
    model_client = get_rotational_model_client(is_research_agent=True)
    model_name = model_client.model  # The string name of the model, e.g., "gemini-2.5-flash"

    # 2. Define the agent's instructions with the user's query embedded
    research_agent_instructions = f"""
    You are a highly intelligent data-formatting machine. Your ONLY function is to research a user's query and output the findings as a single, raw JSON object.

    USER QUERY: '{query}'

    Follow these steps with absolute precision:
    1.  Use the `google_search` tool to find the most relevant and authoritative online sources to answer the user's query.
    2.  Analyze the content from the search results.
    3.  Construct a JSON object that strictly adheres to the `FinalReport` schema.
    4.  For each relevant source, you MUST create one JSON object within the `report` list.
    5.  You MUST map the source URL to the `references` field.
    6.  You MUST extract the Title of the page and map it to the `title` field.
    7.  You MUST extract the Name of the Source (Website Name) and map it to the `source_name` field.

    **CRITICAL RULES FOR OUTPUT:**
    - Your entire response MUST be ONLY the raw JSON object.
    - Do NOT include any introductory text, explanations, or summaries outside of the JSON structure.
    - Do NOT wrap the JSON in markdown backticks (```json ... ```).
    - Your output must begin with `{{` and end with `}}`.

    **EXAMPLE OUTPUT STRUCTURE:**
    ```json
    {{
      "report": [
        {{
          "title": "The Meaning of Life",
          "source_name": "Philosophy Today",
          "summary": "A concise summary of the first relevant source found for the query.",
          "key_excerpts": "A key quote, data point, or direct excerpt from the first source.",
          "references": "https://www.example.com/source1"
        }},
        {{
          "title": "42: The Answer",
          "source_name": "Galaxy Guide",
          "summary": "A concise summary of the second relevant source found for the query.",
          "key_excerpts": "A key quote, data point, or direct excerpt from the second source.",
          "references": "https://www.example.com/source2"
        }}
      ]
    }}
    ```
    Now, perform the research for the query and provide the final JSON object.
    """

    agent_model = model_name.strip()
    print(f"Creating a new research agent with model: {agent_model}")
    research_agent = LlmAgent(
        model=agent_model,
        name="ResearchAgent",
        instruction=research_agent_instructions,
        tools=[google_search],
        output_key="research"
    )

    return research_agent


# --- Refactored Tool Entrypoint ---
@tool
async def web_search_tool(query: str) -> str:
    """
    Performs an internet search using a dynamically created Google ADK agent
    and returns a formatted string of the summarized results.
    """
    logger = get_research_logger()
    
    # Check cache first
    cache = get_search_cache()
    cached_result = cache.get_results(query)
    if cached_result:
        logger.info(f"Cache hit for query: {query[:30]}...")
        return cached_result
    
    session_id = str(uuid.uuid4())  # Generate a unique ID for this search session
    app_name = "neetresearch"
    user_id = "basobaso"

    print(f"\n[bold magenta]Performing ADK-powered web search for query:[/bold magenta] '{query}'")

    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())  # Generate a unique ID for this search session
    await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    print(f"Created new isolated session with ID: {session_id}")

    # 2-4. Create agent and execute with retries for transient provider failures.
    user_content = genai_types.Content(role='user', parts=[genai_types.Part(text=query)])
    final_event = None
    latest_text = None
    max_attempts = 3
    last_error = None
    event_count = 0

    for attempt in range(max_attempts):
        try:
            research_agent = create_dynamic_research_agent(query)
            runner = Runner(agent=research_agent, app_name=app_name, session_service=session_service)
            run_had_text = False
            run_had_final = False

            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=user_content):
                event_count += 1
                event_text = _extract_text_from_event(event)
                if event_text:
                    latest_text = event_text
                    run_had_text = True

                if event.is_final_response():
                    run_had_final = True
                    if event_text:
                        print("Final response received from agent.")
                        final_event = event

            # Only stop retrying when this attempt produced meaningful output.
            if final_event or run_had_text:
                break

            if attempt < max_attempts - 1:
                print(
                    f"ADK run produced no content-bearing events (attempt {attempt + 1}/{max_attempts}, "
                    f"events_seen={event_count}, final_seen={run_had_final}). Retrying..."
                )
                await asyncio.sleep(2)
                continue
        except Exception as e:
            last_error = e
            if attempt < max_attempts - 1:
                print(f"Retrying web search agent after transient failure ({attempt + 1}/{max_attempts}): {e}")
                await asyncio.sleep(2)
                continue
            tb_str = traceback.format_exc()
            return f"An error occurred during agent execution: {e}\n{tb_str}"

    # 5. Process the structured output from the agent.
    structured_output_str = None
    if final_event:
        structured_output_str = _extract_text_from_event(final_event)
    elif latest_text:
        structured_output_str = latest_text
    else:
        # ADK may persist output in session state without emitting a content-bearing final event.
        current_session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )
        if current_session and current_session.state:
            state = current_session.state

            stored_output = state.get("research")
            if stored_output is None:
                # Fallback: sometimes keys are namespaced and not exactly `research`.
                for key, value in state.items():
                    if "research" in str(key).lower():
                        stored_output = value
                        break

            if isinstance(stored_output, str):
                structured_output_str = stored_output
            elif stored_output is not None:
                structured_output_str = json.dumps(stored_output)

    if not structured_output_str:
        return (
            "Agent did not produce a final response for query: "
            f"{query} (events_seen={event_count})."
        )

    try:
        # The ADK agent places the structured JSON output in the text part of the final event
        payload = _extract_json_payload(structured_output_str)
        python_dict = json.loads(payload)
        final_report = FinalReport.model_validate(python_dict)
        normalized_items = _normalize_report_items(final_report.report)

        if not normalized_items:
            return f"The agent's search returned no relevant results to summarize for query: {query}"

    except Exception as e:
        print(f"[bold red]Error parsing structured output from agent:[/bold red]\n{structured_output_str}")
        return f"Failed to parse the structured output. Error: {e}"

    # 6. Format the validated Pydantic objects into the required string format.
    formatted_results = []
    print(f"Search complete. Formatting {len(normalized_items)} result(s).")
    for i, summary_item in enumerate(normalized_items):
        source_str = (
            f"--- SOURCE {i+1} ---\n"
            f"TITLE: {summary_item.title}\n"
            f"SOURCE: {summary_item.source_name}\n"
            f"REFERENCE: {summary_item.references}\n"
            f"SUMMARY:\n{summary_item.summary}\n\n"
            f"KEY EXCERPTS:\n{summary_item.key_excerpts}\n"
            "--------------------"
        )
        formatted_results.append(source_str)

    final_result = "\n\n".join(formatted_results)
    if "--- SOURCE" not in final_result:
        return f"WEB_SEARCH_TOOL_ERROR: No valid sources were formatted for query: {query}"
    
    # Cache the results for future queries
    cache.set_results(query, final_result)
    logger.info(f"Cached results for query: {query[:30]}...")

    return final_result


# --- Example Usage & Testing ---

async def main():
    """
    Main function to run and test the web search tool.
    """
    try:
        # Test Case 1: A technical query
        print("\n" + "=" * 50)
        print("                RUNNING TEST CASE 1")
        print("=" * 50)
        query1 = "What is the current politics in 2025 zimbabwe"
        results = await web_search_tool.ainvoke({"query": query1})
        print("\n[bold green]------ FINAL RESULT for Test Case 1 ------[/bold green]")
        print(results)
        print("[bold green]------------------------------------------[/bold green]\n")

    except Exception as e:
        print(f"An error occurred in the main function: {e}")


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
