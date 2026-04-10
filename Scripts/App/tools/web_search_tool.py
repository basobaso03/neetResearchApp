    # ==============================================================================
#  Prerequisites:
#  1. Install necessary Python packages:
#     pip install crawl4ai langchain-core google-api-python-client python-dotenv langchain_google_genai langchain-community python-magic rich docx2txt "unstructured[pptx]" beautifulsoup4
#
#  2. Install Crawl4AI's browser binaries (one-time setup):
#     crawl4ai-setup
# ==============================================================================

import tempfile
import os
import asyncio
import itertools
from typing import List, Dict, Any
import re
from urllib.error import HTTPError
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# --- Crawl4AI Imports ---
# Import the core components from the Crawl4AI library
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.processors.pdf import PDFCrawlerStrategy
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai .markdown_generation_strategy import DefaultMarkdownGenerator

# --- Langchain & Other Imports ---
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import (
    PyPDFLoader, # PyPDFLoader is kept for local file loading if needed, but Crawl4AI handles online PDFs
    Docx2txtLoader,
    UnstructuredPowerPointLoader,
    BSHTMLLoader
)
from googleapiclient.discovery import build
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import time
from rich import print
from Scripts.App.config import MODEL_CONFIG, get_api_key
from Scripts.App.config.api_key_manager import get_api_key_manager

# Load environment variables for keys and configurations
load_dotenv()

# --- Model Pool for High-Frequency Summarization Tasks ---
# A consolidated and unique list of fast, efficient models for summarization.
ROTATIONAL_MODELS = [
    "gemini-2.5-flash-lite",
]

# Mapping file extensions to their corresponding LangChain loader classes.
# This is still needed for files that Crawl4AI downloads but doesn't natively parse (e.g., .docx).
LOADER_MAPPING = {
    ".pdf": PyPDFLoader, # Maintained for potential local file use cases
    ".docx": Docx2txtLoader,
    ".pptx": UnstructuredPowerPointLoader,
    ".html": BSHTMLLoader, # Kept for completeness, though Crawl4AI's Markdown is superior
}

# Create an iterator that cycles through the models indefinitely for load balancing.
model_cycler = itertools.cycle(ROTATIONAL_MODELS)



class WebsearchCleaningTools:
    """
    A collection of tools for web searching and content summarization.
    """
    def __init__(self):
        pass
        # Define the set of English stop words
        self.STOP_WORDS = set(stopwords.words('english'))

    def clean_and_normalize_text(self, text: str) -> str:
        """
        Performs lowercasing, punctuation/noise removal, and stop word filtering.
        """
        if not text:
            return ""

        # 1. Lowercase conversion
        text = text.lower()
        
        # 2. Remove all remaining HTML tags (a failsafe, though trafilatura should handle most)
        text = re.sub(r'<.*?>', ' ', text)
        
        # 3. Remove email addresses and URLs
        text = re.sub(r'\S*@\S*\s?', ' ', text)  # Emails
        text = re.sub(r'https?://\S+|www\.\S+', ' ', text) # URLs
        
        # 4. Remove non-alphanumeric characters (keep basic punctuation like . ,)
        # This regex keeps letters, numbers, and spaces. Adjust if you need to keep specific punctuation.
        text = re.sub(r'[^a-z0-9\s.,]', ' ', text)
        
        # 5. Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 6. Optional: Tokenization and Stop Word Removal (can be skipped for modern LLMs)
        # The agent's LLM will perform its own tokenization, but this pre-filtering can save cost/time.
        tokens = word_tokenize(text)
        filtered_tokens = [word for word in tokens if word not in self.STOP_WORDS and len(word) > 1]
        
        return ' '.join(filtered_tokens)



def get_rotational_model_client(is_supervisor=False, is_research_agent=False, temperature=0.0, max_retries=0):
    """
    Returns a ChatGoogleGenerativeAI client with the next model from the
    rotational pool and automatic retries configured. This helps distribute
    the load and avoid rate limiting.
    """
    print("Selecting next model from rotation...")
    api_key = None
    
    supervisor_models = ["gemini-2.5-flash-lite"]
    
    model_name = next(model_cycler)

    if is_supervisor:
        api_key = get_api_key("supervisor")
        # If the current model is not a supervisor model, cycle until we get one
        while model_name not in supervisor_models:
            model_name = next(model_cycler)
    elif is_research_agent:
        api_key = get_api_key("research")
        # Research agents can use both Flash and Flash-Lite for quota resilience.
    else:
        api_key = get_api_key("summarization")

    print(f"Selected model: {model_name}")
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_retries=max_retries,
        timeout=MODEL_CONFIG.llm_timeout,
        google_api_key=api_key # Use environment variable for the key
    )

# Pydantic schema for ensuring the summarizer returns structured JSON output.
class SummarySchema(BaseModel):
    """Represents a summary and key excerpts of content for citation."""
    summary: str = Field(..., description="A concise summary of the content relevant to the user's query.")
    key_excerpts: str = Field(..., description="Key quotes, excerpts, examples or illustrations that directly address the user's query.")
    metadata: str = Field(..., description="Metadata from the source document (like filename) to be used for citation.")


async def summarize_content(doc, query, is_database: bool = False, max_retries=3):
    """
    Asynchronously summarizes a single document's content using a rotational pool
    of generative models to ensure high throughput and reliability.
    This function's logic remains unchanged by the refactoring.
    """
    # The summarization logic is independent of the scraper and remains the same.
    # It now benefits from receiving cleaner, Markdown-formatted content.
    page_content = "\n".join(doc) if is_database else doc.page_content[:100000]
    prompt = f"""
You are an expert AI assistant specializing in parsing and summarizing research materials. Your task is to process a given text block and return a structured JSON object.

**Input Format:**
You will be given a single block of text below. This block contains two parts:
1.  The 'Content' to be analyzed.
2.  A 'Metadata' section for citation.

**Your Task:**
1.  First, carefully identify the 'Content' and the 'Metadata' sections within the provided text.
2.  Read the 'Content' and analyze it in the context of the following user query: "{query}"
3.  Create a concise summary of the content as it relates to the user's query.
4.  Extract the most relevant key excerpts, examples, illustrations, or data points from the content that directly address the query.
5.  **CRITICAL:** You must copy the 'Metadata' section *Important for future academic citations*, without any changes or alterations, and place it into the 'metadata'.

---
**BEGIN TEXT BLOCK**
{page_content}
---
**END TEXT BLOCK**
"""
    for attempt in range(max_retries):
        rotational_summarizer = get_rotational_model_client()
        structured_summarizer = rotational_summarizer.with_structured_output(SummarySchema)
        try:
            print(f"Attempt {attempt + 1} to summarize content...")
            response = await structured_summarizer.ainvoke(prompt)
            if response is not None:
                print("Summarization successful.")
                return response
            else:
                print(f"Attempt {attempt + 1} returned {response}. Retrying...")
                await asyncio.sleep(2)
        except Exception as e:
            print(f"An Error occurred during summarization attempt {attempt + 1}: {e}. Retrying...")
            await asyncio.sleep(2)

    print(f"Failed to summarize content after {max_retries} attempts. Returning fallback data.")
    return SummarySchema(summary=page_content[:10000] + "...", key_excerpts="Could not extract.", metadata="Source metadata unavailable.")

# --- REFACTORED GoogleSearchTool with Crawl4AI ---
class GoogleSearchTool:
    """
    A tool that combines Google Custom Search with Crawl4AI for advanced web scraping.
    It finds relevant URLs and intelligently extracts clean, AI-ready content from them,
    handling web pages, PDFs, and other documents seamlessly.
    """

    def __init__(self, api_keys: List[str], cse_ids: List[str], num_results: int = 3):
        """
        Initializes the GoogleSearchTool and its long-lived AsyncWebCrawler instance.
        """
        if not api_keys or not cse_ids:
            raise ValueError("Google Custom Search API keys and CSE IDs must be provided.")

        self.api_keys = api_keys
        self.cse_ids = cse_ids
        self._api_key_cycler = itertools.cycle(self.api_keys)
        self._cse_cycler = itertools.cycle(self.cse_ids)
        self.num_results = num_results
        self.web_cleaner = WebsearchCleaningTools()

    def _build_service(self, api_key: str):
        # The googleapiclient is synchronous, so it is fine to initialize per request.
        return build("customsearch", "v1", developerKey=api_key, cache_discovery=False)

    async def _scrape_and_load_urls(self, urls: List[str]) -> List[Document]:
        """
        Asynchronously processes a list of URLs using Crawl4AI's specialized strategies.
        This single method replaces the previous _scrape_text_from_url, _download_and_load_file,
        and _process_urls methods, greatly simplifying the code.

        By creating the AsyncWebCrawler within an `async with` block, we ensure that
        all browser resources are properly managed and shut down for each scraping
        session, preventing event loop errors.
        """
        documents = []
        # --- Define Crawl4AI Configurations ---
        # Configuration for scraping standard web pages into clean Markdown.
        html_config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter()  # 'PruningContentFilter' intelligently removes boilerplate like ads and navbars.
            ),
            cache_mode=CacheMode.BYPASS # Always fetch fresh data for the agent.
        )
        # PDF configuration can be simplified or merged if behavior is similar.
        pdf_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

        # --- Segregate URLs by Type ---
        # Separate URLs to apply the most effective scraping strategy for each type.
        html_urls = [u for u in urls if u.lower().endswith(('.html', '.htm')) or not any(u.lower().endswith(ext) for ext in LOADER_MAPPING)]
        pdf_urls = [u for u in urls if u.lower().endswith('.pdf')]
        other_doc_urls = [u for u in urls if any(u.lower().endswith(ext) for ext in ['.docx', '.pptx'])]

        # Use a single `async with` block to manage the crawler's lifecycle.
        browser_config = BrowserConfig(headless=True, user_agent_mode="random")
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # --- Process URLs in Parallel ---
            # Process all HTML and PDF pages concurrently for maximum efficiency.
            if html_urls:
                print(f"Scraping {len(html_urls)} web pages...")
                html_results = await crawler.arun_many(html_urls, html_config)
                for result in html_results:
                    if result.success and result.markdown:
                        documents.append(Document(page_content=result.markdown.raw_markdown, metadata={"source": result.url}))

            if pdf_urls:
                print(f"Extracting content from {len(pdf_urls)} PDFs...")
                pdf_results = await crawler.arun_many(pdf_urls, pdf_config)
                for result in pdf_results:
                    if result.success and result.markdown and hasattr(result.markdown, 'raw_markdown'):
                        documents.append(Document(page_content=result.markdown.raw_markdown, metadata={"source": result.url, "other":result.metadata}))

            # --- Handle Other Document Types (Hybrid Approach) ---
            # For formats Crawl4AI doesn't parse natively, use its download feature
            # combined with LangChain's loaders.
            if other_doc_urls:
                print(f"Downloading and loading {len(other_doc_urls)} other documents...")
                for url in other_doc_urls:
                    try:
                        # Configure the crawler to accept and handle file downloads.
                        download_config = CrawlerRunConfig(accept_downloads=True, cache_mode=CacheMode.BYPASS)
                        result = await crawler.arun(url, download_config)
                        if result.success and result.downloads:
                            # Process the first downloaded file.
                            download_path = result.downloads[0].path
                            ext = result.downloads[0].extension
                            loader_cls = LOADER_MAPPING[ext]
                            loader = loader_cls(download_path)
                            docs = loader.load()
                            # Add source metadata to the loaded documents.
                            for doc in docs:
                                doc.page_content = self.web_cleaner.clean_and_normalize_text(doc.page_content)[:100000]
                                doc.metadata["source"] = url
                            documents.extend(docs)
                            os.remove(download_path) # Clean up the temporary downloaded file.
                    except Exception as e:
                        print(f"Failed to process document {url}: {e}")

        return documents

    async def search_and_scrape(self, query: str) -> Dict[str, Any]:
        """
        Searches for a query using Google, then uses the refactored Crawl4AI-based
        method to scrape the top results and return their content.
        """
        print(f"Searching for: '{query}' using Google Search...")
        if not self.api_keys:
            return {
                'status': "error",
                'message': "WEB_SEARCH_TOOL_ERROR: No Google Search API keys are configured.",
                'content': []
            }
        if not self.cse_ids:
            return {
                'status': "error",
                'message': "WEB_SEARCH_TOOL_ERROR: No Google CSE IDs are configured.",
                'content': []
            }

        search_results = []
        errors = []
        key_count = len(self.api_keys)
        cse_count = len(self.cse_ids)

        # Try every key/CSE combination for the current query.
        for _ in range(key_count):
            api_key = next(self._api_key_cycler)
            for _ in range(cse_count):
                cse_id = next(self._cse_cycler)
                try:
                    service = self._build_service(api_key)
                    search_results_response = service.cse().list(
                        q=query, cx=cse_id, num=self.num_results,
                    ).execute()
                    search_results = search_results_response.get('items', [])
                    print(f"Found {len(search_results)} results.")
                    if search_results:
                        break
                except HTTPError as e:
                    status_code = getattr(e, "code", "unknown")
                    errors.append(f"HTTPError {status_code} for current key/CSE: {e}")
                    print(f"Google Search HTTPError ({status_code}); trying next key/CSE pair.")
                    continue
                except Exception as e:
                    errors.append(f"Google Search API call failed: {e}")
                    continue
            if search_results:
                break

        if not search_results and errors:
            return {
                'status': "error",
                'message': "WEB_SEARCH_TOOL_ERROR: All Google Search key/CSE combinations failed.",
                'content': [],
                'errors': errors,
            }

        if not search_results:
            return {'status': "success", 'message': "No search results found.", 'content': []}

        urls = [result.get('link') for result in search_results if result.get('link')]
        print(f"Processing content from the top {len(urls)} results with Crawl4AI...")

        # --- Call the new, unified scraping method ---
        scraped_documents = await self._scrape_and_load_urls(urls)

        return {
            'status': "success",
            'message': f"Successfully processed {len(scraped_documents)} URLs.",
            'content': scraped_documents
        }

# --- Tool Initialization and Execution ---
def _collect_google_search_api_keys() -> List[str]:
    """Collect all active Google keys discovered by the shared key manager."""
    keys = []

    try:
        manager = get_api_key_manager()
        keys = [k for k in manager.get_all_keys() if k and k.strip()]
    except Exception as e:
        print(f"WARNING: Could not load key manager pool, falling back to env scan: {e}")

    if keys:
        return list(dict.fromkeys([k.strip() for k in keys]))

    # Fallback: scan env for common Google key naming patterns.
    discovered = []
    for env_name, env_value in os.environ.items():
        if not env_value or not env_value.strip():
            continue
        lowered = env_name.lower()
        is_google_key_name = lowered.startswith("google_api_key") or lowered.endswith("_api_key")
        if is_google_key_name and env_value.strip().startswith("AIza"):
            discovered.append(env_value.strip())

    return list(dict.fromkeys(discovered))


def _collect_google_cse_ids() -> List[str]:
    """Collect all configured Google CSE IDs from environment variables."""
    ids = []
    for env_name, env_value in os.environ.items():
        if not env_value or not env_value.strip():
            continue

        lowered = env_name.lower()
        if lowered == "google_cse_id" or re.match(r"^google_cse_id\d+$", lowered):
            ids.append(env_value.strip())

    return list(dict.fromkeys(ids))

# Initialize the refactored tool
search_tool = GoogleSearchTool(
    api_keys=_collect_google_search_api_keys(),
    cse_ids=_collect_google_cse_ids(),
    num_results=3,
)

@tool
async def web_search_tool(query: str) -> str:
    """
    A powerful fallback tool that searches the public internet.
    Use this tool ONLY WHEN primary, internal tools have failed to provide a relevant or up-to-date answer.
    This tool is essential for finding information on recent events or very specific topics.
    """
    print(f"Performing web search for query: {query}")

    search_result_dict = await search_tool.search_and_scrape(query)
    if search_result_dict.get("status") == "error":
        details = search_result_dict.get("message", "unknown web search error")
        raw_errors = search_result_dict.get("errors", [])
        if raw_errors:
            details = f"{details} | attempts: {' ; '.join(raw_errors[:3])}"
        return f"WEB_SEARCH_TOOL_ERROR: {details}"

    try:
        docs: List[Document] = search_result_dict.get('content', [])
        if not docs:
             return f"No web results with content found for query: {query}"
    except Exception as e:
        return f"Error loading web content: {e}"

    # The summarization part remains unchanged and benefits from cleaner input data.
    summarization_tasks = [summarize_content(doc, query) for doc in docs]
    summaries = await asyncio.gather(*summarization_tasks)

    formatted_results = []
    for i, (doc, doc_summary) in enumerate(zip(docs, summaries)):
        if doc_summary and isinstance(doc_summary, SummarySchema):
            source_str = (
                f"--- SOURCE {i+1} ---\n"
                f"URL: {doc.metadata.get('source', 'N/A')}\n"
                f"SUMMARY:\n{doc_summary.summary}\n\n"
                f"KEY EXCERPTS:\n{doc_summary.key_excerpts}\n"
                "--------------------"
            )
            formatted_results.append(source_str)

    return "\n\n".join(formatted_results) if formatted_results else f"No web results could be summarized for query: {query}"


# --- Example Usage ---
async def main():
    # Example query that might return web pages and PDFs
    query = "what are the core principles of retrieval-augmented generation"
    results = await web_search_tool.ainvoke({"query": query})
    print(results)

if __name__ == "__main__":
    # To run this standalone script and ensure graceful shutdown of background
    # processes on all platforms (especially Windows), we manage the asyncio
    # event loop manually.
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        # This part is crucial. It gives any pending tasks (like browser shutdown)
        # a moment to complete before the loop is finally closed.
        print("Closing the event loop...")
        tasks = asyncio.all_tasks(loop=loop)
        for task in tasks:
            task.cancel()
        group = asyncio.gather(*tasks, return_exceptions=True)
        loop.run_until_complete(group)
        loop.close()
        print("Event loop closed.")
