
import os
import asyncio
import itertools
import uuid
import sys
from typing import List, Annotated
import time
import json
from google import genai as gn
# --- ADK & Google Imports ---
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService


from google.genai import types as genai_types
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.tools import tool

# --- Utility Imports ---
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import rich
from rich import print

from Scripts.App.database.database import RetrievalTool

# Load environment variables from .env file
load_dotenv()


# --- Model Pool for High-Frequency Tasks ---
# A consolidated and unique list of fast, efficient models.
ROTATIONAL_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]

# Create an iterator that cycles through the models indefinitely for load balancing.
model_cycler = itertools.cycle(ROTATIONAL_MODELS)

# make model_name global
model_name = None

db_retrieval_tool = None

def set_database(retrieval_tool: RetrievalTool):
    global db_retrieval_tool
    db_retrieval_tool = retrieval_tool
    

def get_rotational_model_client(is_supervisor=False, is_research_agent=False, temperature=0.0, max_retries=3):
    """
    Returns a ChatGoogleGenerativeAI client with the next model from the
    rotational pool. This function is HEAVILY USED by other modules and is
    preserved in its original form.
    """
    print("Waiting for 6 seconds to get your next model....")

    supervisor_models = ["gemini-2.5-flash", "gemini-2.5-flash"]
    research_model_exclude = ["gemini-2.5-flash-lite"]


import os
import asyncio
import itertools
import uuid
import sys
from typing import List, Annotated
import time
import json
from google import genai as gn
# --- ADK & Google Imports ---
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService


from google.genai import types as genai_types
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.tools import tool

# --- Utility Imports ---
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import rich
from rich import print

from Scripts.App.database.database import RetrievalTool

# Load environment variables from .env file
load_dotenv()


# --- Model Pool for High-Frequency Tasks ---
# A consolidated and unique list of fast, efficient models.
ROTATIONAL_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

# Create an iterator that cycles through the models indefinitely for load balancing.
model_cycler = itertools.cycle(ROTATIONAL_MODELS)

# make model_name global
model_name = None

db_retrieval_tool = None

def set_database(retrieval_tool: RetrievalTool):
    global db_retrieval_tool
    db_retrieval_tool = retrieval_tool
    

def get_rotational_model_client(is_supervisor=False, is_research_agent=False, temperature=0.0, max_retries=3):
    """
    Returns a ChatGoogleGenerativeAI client with the next model from the
    rotational pool. This function is HEAVILY USED by other modules and is
    preserved in its original form.
    """
    print("Waiting for 6 seconds to get your next model....")

    supervisor_models = ["gemini-2.5-flash", "gemini-2.5-flash"]
    research_model_exclude = ["gemini-2.5-flash-lite"]

    time.sleep(6) # A delay to respect API rate limits
    model_name = next(model_cycler)

    if is_supervisor:
        while model_name not in supervisor_models:
            model_name = next(model_cycler)
    else:
        # Example of excluding the most powerful model for simple tasks
        while model_name == "gemini-2.5-flash-lite":
            model_name = next(model_cycler)

    print(f"--- Done waiting. Your next model is: [bold green]{model_name}[/bold green] ---")
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_retries=max_retries,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

# --- Pydantic Schemas for Structured Output ---

class SummarySchema(BaseModel):
    """Represents a summary and key excerpts of content for citation."""
    title: str = Field(..., description="The title of the book or document.")
    author: str = Field(..., description="The author(s) of the book or document.")
    year: str = Field(..., description="The year of publication.")
    publisher: str = Field(..., description="The publisher of the book or document.")
    summary: str = Field(..., description="A concise summary of the content relevant to the user's query.")
    key_excerpts: str = Field(..., description="Key quotes, excerpts, examples or illustrations that directly address the user's query.")
    reference: str = Field(..., description="Here must be the full references of the books in Havard citation style. use the book infomation to create these references.")

class FinalReport(BaseModel):
    """A final report containing summaries of all relevant web search results."""
    report: List[SummarySchema] = Field(..., description="A list of summaries from processed web pages.")



# --- Graph Tools for Database Interaction ---

async def similarity_search(query: str) -> str:
        """
        Use this tool to find the most specific, focused, and top-ranked documents
        for a direct question. It's best for getting the most relevant answer quickly.
        """
        print(f"Performing similarity search for query: '{query}'")

        docs_query =  db_retrieval_tool.query( query_text=query)

        if not docs_query:
            return {"status": "error",
                    "tool_response": "No relevant documents found in the database or tool failed."}

        query_formatted_results=[]
        for i, (doc, metadata) in enumerate(zip(docs_query["documents"][0], docs_query["metadatas"][0])):
            title = metadata.get('title') or metadata.get('journal_title', 'N/A')
            source_str = (
                f"--- Book {i+1} ---\n"
                "<Book Infomation>\n"
                f"TITLE: {title}\n"
                f"AUTHOR: {metadata.get('author', 'N/A')}\n"
                f"PUBLISHER: {metadata.get('publisher', 'N/A')}\n"
                f"YEAR: {metadata.get('creationdate', 'N/A')[:4]}\n"
                f"PAGE NUMBER: {metadata.get('page', 'N/A')}\n"
                f"VOLUME: {metadata.get('volume', 'N/A')}\n"
                f"ISSUE: {metadata.get('issue', 'N/A')}\n"
                f"DOI URL: {metadata.get('doi_url', 'N/A')}\n"
                f"ACCESS DATE: {metadata.get('access_date', 'N/A')}\n"
                f"BOOK NAME: {metadata.get('source', 'N/A')}\n"
                f"PAGE RANGE: {metadata.get('page_range', 'N/A')}\n"
                f"EDITION: {metadata.get('edition', 'N/A')}\n"
                f"PLACE: {metadata.get('place', 'N/A')}\n"
                "<Book Infomation>\n"
                "<Book Content>\n"
                f"{doc}\n"
                "<Book Content>"
            )
            query_formatted_results.append(source_str)

        return {"status": "success",
                "tool_response": "\n\n".join(query_formatted_results)}
        
async def diverse_search(query: str) -> str:
        """
        Use this tool for broader research questions to get a diverse set of documents
        covering multiple aspects of a topic, while actively avoiding redundant information.
        """
        
        print(f"Performing diverse (MMR) search for query: '{query}'")

        docs_mmr =  db_retrieval_tool.query_with_mmr( query_text=query)
        #print(f"Docs: {docs}")
        if not docs_mmr:
            return {"status": "error",
                    "tool_response": "No relevant documents found in the database or tool failed."}
        mmr_formatted_results = []
        for i, doc in enumerate(docs_mmr):
            title = doc.metadata.get('title') or doc.metadata.get('journal_title', 'N-A')
            source_str = (
                f"--- Book {i+1} ---\n"
                "<Book Infomation>\n"
                f"TITLE: {title}\n"
                f"AUTHOR: {doc.metadata.get('author', 'N/A')}\n"
                f"PUBLISHER: {doc.metadata.get('publisher', 'N/A')}\n"
                f"YEAR: {doc.metadata.get('creationdate', 'N/A')[:4]}\n"
                f"PAGE NUMBER: {doc.metadata.get('page', 'N/A')}\n"
                f"VOLUME: {doc.metadata.get('volume', 'N/A')}\n"
                f"ISSUE: {doc.metadata.get('issue', 'N/A')}\n"
                f"DOI URL: {doc.metadata.get('doi_url', 'N/A')}\n"
                f"ACCESS DATE: {doc.metadata.get('access_date', 'N/A')}\n"
                f"BOOK NAME: {doc.metadata.get('source', 'N/A')}\n"
                f"PAGE RANGE: {doc.metadata.get('page_range', 'N/A')}\n"
                f"EDITION: {doc.metadata.get('edition', 'N/A')}\n"
                f"PLACE: {doc.metadata.get('place', 'N/A')}\n"
                "<Book Infomation>\n"
                "<Book Content>\n"
                f"{doc.page_content}\n"
                "<Book Content>"
            )
            mmr_formatted_results.append(source_str)

        return {"status": "success",
                "tool_response": "\n\n".join(mmr_formatted_results)}

async def think_tool(thought: str) -> None:
    """
    A simple tool that allows the agent to log its thoughts.
    """
    print("\n[bold yellow]🤖 Database Agent is thinking...[/bold yellow]")
    await asyncio.sleep(6)  # Simulate processing delay
    print("\n============================================== Database Agent Thoughts ===============================================\n")
    rich.print(f"[bold yellow]💭 Agent Thought: {thought}[/bold yellow]")
    print("\n=====================================================================================================================\n")
    


# --- ADK Agent Factory ---

def create_dynamic_research_agent(query: str) -> LlmAgent:
    """
    Creates and returns a new ADK research agent instance using a model
    from the rotational pool. This ensures each search task can use a
    different, dynamically selected model.
    """
    # 1. Get the next model client from the existing rotational function
    model_client = get_rotational_model_client(is_research_agent=True)
    model_name = model_client.model # The string name of the model, e.g., "gemini-2.5-flash"

    # 2. Define the agent's instructions with the user's query embedded
    research_agent_instructions = f"""
    You are a highly intelligent and meticulous research assistant. Your purpose is to conduct research on a user's query by interacting with a local database and format the findings into a single, raw JSON object.

    USER QUERY: '{query}'

    **AVAILABLE TOOLS:**
    1. `similarity_search(query: str)`: Use this for specific, direct questions to find the most focused and top-ranked documents.
    2. `diverse_search(query: str)`: Use this for broader research questions to get a wide range of documents covering multiple aspects of a topic.
    3. `think_tool(thought: str)`: You MUST use this tool to reflect on your search results and plan your next steps.

    **RESEARCH PROCESS:**
    1.  Start by using the `similarity_search` or `diverse_search` tool with the initial user query.
    2.  **CRITICAL:** After every search, you MUST use the `think_tool` to analyze the results. In your thought, state whether the results are sufficient or if you need to refine your search.
    3.  If the results are insufficient, formulate a new, more refined query and perform another search. You can repeat this process.
    4.  You have a **hard limit of 5 searches per tool**. Keep track of your search attempts.
    5.  Once you have gathered sufficient information, construct a JSON object that strictly adheres to the `FinalReport` schema.

    **SCHEMA AND CITATION RULES:**
    - For each relevant source document, create one JSON object within the `report` list.
    - The source text will contain a `<Book Infomation>` section. Use this information for all citations.
    - `title`: Extract the title from the book information.
    - `author`: Extract the author from the book information.
    - `year`: Extract the year from the book information.
    - `publisher`: Extract the publisher from the book information.
    - `summary`: Your summary MUST include in-text citations where appropriate, created from the book information.
    - `key_excerpts`: Your key excerpts MUST include in-text citations, created from the book information.
    - `reference`: This field MUST contain a full references separated by `-`for the books in the Harvard citation style.These references MUST be created using the book information. Avoid inventing any citation details.
    - If the book information is insufficient for a full Harvard reference, state that clearly in the `reference` field and provide only the book's title. Do NOT invent citation details.

    **CRITICAL RULES FOR OUTPUT:**
    - Your entire response MUST be ONLY the valid raw JSON object.
    - Do NOT include any introductory text, explanations, or summaries outside of the JSON structure.
    
    **EXAMPLE JSON STRUCTURE:**
    ```json
    {{
      "report": [
        {{
          "title": "Title of Book",
          "author": "Author Name",
          "year": "2023",
          "publisher": "Publisher Name",
          "summary": "This is a summary of the book's content (Author, Year).",
          "key_excerpts": "\\"This is a direct quote from the book\\" (Author, Year, p.PageNumber).",
          "reference": "- Author, A. (Year) Title of Book. Publisher. - ..."
        }}
      ]
    }}
    ```
    Now, perform the research for the query and provide the final JSON object.
    """

   
    agent_model = model_name.strip()[7:]
    print(f"Creating a new research agent with model: {agent_model}")
    research_agent = LlmAgent(
        model=agent_model,
        name="DBResearchAgent",
        instruction=research_agent_instructions,
        tools=[think_tool, similarity_search, diverse_search],
        output_key="research"

    )
     
    return research_agent


def formatter_agent(text : str,model_name:str = "gemini-2.5-flash") :
    """
    Creates an agent that formats raw text into the FinalReport schema.
    This agent has no tools.
    """
    formatter_instructions = f"""
    You are a meticulous data formatting assistant.
    You will be given a block of text containing research findings.
    Your task is to carefully read the text and structure it into a valid JSON object
    that strictly adheres to the FinalReport schema.
    Do not change any content of the original text just format it to fit the required schema.


    The research findings are available in the session state under the key 'research'.
    Use this data: {text}

    **SCHEMA AND CITATION RULES:**
    - For each relevant source, create one JSON object in the 'report' list.
    - `summary`: Your summary MUST include in-text citations.
    - `key_excerpts`: Your key excerpts MUST include in-text citations.
    - `reference`: This field MUST contain a full references separated by `-` for each source in Harvard style.
    """
    client = gn.Client()
    response = client.models.generate_content(
        model=model_name,
        contents=formatter_instructions,
        config={
            "response_mime_type": "application/json",
            "response_schema": FinalReport,
        },
    )
    # Use the response as a JSON string.
    #print(response.parsed)
    
    return response.parsed

        # output_schema=FinalReport,
# --- Refactored Tool Entrypoint ---
@tool
async def database_search_tool(query: str) -> str:
    """
    Performs an internet search using a dynamically created Google ADK agent
    and returns a formatted string of the summarized results.
    """
    session_id = str(uuid.uuid4()) # Generate a unique ID for this search session
    final_response = None
    final_response_content=None
    max_retries = 3

    for attempt in range(max_retries):
        print(f"\n[bold yellow]Attempt {attempt + 1} of {max_retries} for query: '{query}'[/bold yellow]")
        app_name="neetresearchdb"
        user_id = "basobasodb"

        print(f"\n[bold magenta]🚀 Performing ADK-powered database search for query:[/bold magenta] '{query}'")

        session_service = InMemorySessionService()
        session_id = str(uuid.uuid4()) # Generate a unique ID for this search session
        await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id) # Removed 'id' argument
        print(f"Created new isolated session with ID: {session_id}") # Modified print statement

        # 2. Create a new agent with a rotated model for this specific query.
        try:
            research_agent = create_dynamic_research_agent(query)
           
        except Exception as e:
            print(f"[bold red]Error creating the internal db research agent: {e} [/bold red]\n")
            return f"Error creating the research agent: {e}"

        # 3. Setup and run the ADK Runner.
        runner = Runner(agent=research_agent, app_name=app_name, session_service=session_service)

        # 4. Execute the agent asynchronously and wait for the final response.
        user_content = genai_types.Content(role='user',parts=[genai_types.Part(text=query)])
        try:
            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=user_content):
                if event.is_final_response() and event.content and event.content.parts:
                    final_response_content = event.content.parts[0].text
        except Exception as e:
            print(f"[bold red]Error during agent execution on attempt {attempt + 1}: {e} [/bold red]\n")
            if attempt == max_retries - 1:
                return f"An error occurred during agent execution: {e}"
            continue # Move to the next attempt

        

        # 5. Process the structured output from the agent.
        current_session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        stored_output = current_session.state.get("research", None)
        final_response=stored_output

        if final_response_content is not None and final_response is not None:
            break # Exit loop if we have a response
        else:
            print(f"[bold yellow]No final response on attempt {attempt + 1}. Retrying...[/bold yellow]")
            continue

    if final_response is None:
        print(f"[bold red]Error: Agent did not produce a final response for query after {max_retries} attempts: {query} [/bold red]")
        return f"Agent did not produce a final response for query: {query}"

    try:
        # The ADK agent places the structured JSON output in the text part of the final event
        # structured_output_str = formatter_agent(final_respose)

        # cleaned_text = structured_output_str.replace('\\', '').replace('\n', '').replace('\t', '').replace("```json",'').replace("```","")
        # python_dict = json.loads(cleaned_text)
        # final_report = FinalReport.model_validate(python_dict)
        format_tries = 3
        models=["gemini-2.5-flash-lite","gemini-2.5-flash"]
        for fmt_try in range(format_tries):
            try:
                print(f"\n[bold blue]Formatting attempt {fmt_try + 1} of {format_tries}[/bold blue]")
                final_report = formatter_agent(final_response, model_name=models[fmt_try])
                if final_report.report:
                    break
            except Exception as e:
                print(f"[bold red]Error during formatting attempt {fmt_try + 1}: {e} [/bold red]\n")
                if fmt_try == format_tries - 1:
                    raise e
                continue
        if not final_report.report:
            final_report = formatter_agent(final_response)

        if not final_report.report:
             print(f"The agent's search returned no relevant results to summarize for query: {query}")
             return f"The agent's search returned no relevant results to summarize for query: {query}"

    except Exception as e:
        print(f"[bold red]Error parsing structured output from agent: {e} [/bold red]\n")
        return f"Failed to parse the structured output. Error: {e}"

    # 6. Format the validated Pydantic objects into the required string format.
    formatted_results = []
    print("\n[bold blue]✅ Search Complete. Formatting Results:[/bold blue]")
    for i, summary_item in enumerate(final_report.report):
        source_str = (
            f"--- SOURCE {i+1} ---\n"
            f"TITLE: {summary_item.title}\n"
            f"AUTHOR: {summary_item.author}\n"
            f"YEAR: {summary_item.year}\n"
            f"PUBLISHER: {summary_item.publisher}\n"
            f"SUMMARY:\n{summary_item.summary}\n\n"
            f"KEY EXCERPTS:\n{summary_item.key_excerpts}\n"
            f"REFERENCE: {summary_item.reference}\n"
            "--------------------"
        )
        formatted_results.append(source_str)
    tool_response ="\n\n".join(formatted_results)
    print(f"\n[bold blue]✅ Search Complete. Final Tool Response:[/bold blue]\n{tool_response}")
    return tool_response


# --- Example Usage & Testing ---

async def main():
    """
    Main function to run and test the web search tool.
    """
    try:
        # Test Case 1: A technical query
        print("Initializing RetrievalTool for database search...")
        db_tool = RetrievalTool("../database/db")
        print("RetrievalTool initialized.")
        await set_database(db_tool)
        collections = db_tool.list_collections()
        db_tool.set_collection_name(collection_name=collections[4])
        print("\n" + "="*50)
        print("                🧪 RUNNING TEST CASE 1 🧪")
        print("="*50)
        query1 = "Marketing segmentation techniques for e-commerce businesses"
        results = await database_search_tool.ainvoke({"query": query1})
        print("\n[bold green]------ FINAL RESULT for Test Case 1 ------[/bold green]")
        print(results)
        print("[bold green]------------------------------------------[/bold green]\n")


    except Exception as e:
        print(f"An error occurred in the main function: {e}")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())

