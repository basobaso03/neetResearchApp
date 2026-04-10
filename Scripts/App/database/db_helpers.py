import itertools
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
import time
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import fitz
import base64
from pathlib import Path
import rich
from rich import print

# ----------------------------------------------------------------------
# 1. Unified Document Metadata Model
# ----------------------------------------------------------------------

class DocumentMetadata(BaseModel):
    """
    Unified Pydantic model for document metadata extraction (Textbooks, Journals, etc.).
    """
    document_type: Literal["textbook", "journal_article", "other"] = Field(
        ...,
        description="The type of the document."
    )
    title: str = Field(
        default="N/A",
        description="The full title of the document."
    )
    author: str = Field(
        default="N/A",
        description="The author(s) or editor(s). Format: 'Last, F.M.' or 'Smith, J. and Doe, A.'"
    )
    year: str = Field(
        default="N/A",
        description="The year of publication (YYYY)."
    )
    publisher: str = Field(
        default="N/A",
        description="The publisher name (for books)."
    )
    journal_title: str = Field(
        default="N/A",
        description="The full title of the journal (for articles)."
    )
    volume: str = Field(
        default="N/A",
        description="The volume number."
    )
    issue: str = Field(
        default="N/A",
        description="The issue number."
    )
    page_range: str = Field(
        default="N/A",
        description="The page range (e.g., 'pp. 12-45')."
    )
    doi_url: str = Field(
        default="N/A",
        description="The DOI or URL."
    )
    edition: str = Field(
        default="N/A",
        description="The edition (e.g., '2nd edn.')."
    )
    place: str = Field(
        default="N/A",
        description="The place of publication."
    )

# ----------------------------------------------------------------------
# 2. Prompts
# ----------------------------------------------------------------------

unified_metadata_extract_prompt = """
You are an expert research librarian and metadata extraction specialist.
Your task is to analyze the provided images (the first few pages of a document) and extract precise bibliographic metadata for Harvard-style citations.

**Instructions:**
1.  **Identify Document Type**: Determine if the document is a 'textbook', 'journal_article', or 'other'.
2.  **Extract Fields**: Extract the following fields based on the document type. If a field is not found, use "N/A".

**Fields to Extract:**
*   **title**: Full title of the work.
*   **author**: Author(s) or Editor(s). Standardize to "Last, Initials" (e.g., "Smith, J.").
*   **year**: Publication year (YYYY).
*   **publisher**: Publisher name (mostly for books).
*   **journal_title**: Name of the journal (for articles).
*   **volume**: Volume number.
*   **issue**: Issue number.
*   **page_range**: Page range (e.g., "pp. 10-20").
*   **doi_url**: DOI or URL.
*   **edition**: Edition (e.g., "2nd edn.").
*   **place**: City of publication.

**Crucial:**
*   Look at ALL provided images to gather the information. The copyright page (usually page 2 or 3) often contains the year, publisher, and edition.
*   Be accurate. Do not guess.
"""

# ----------------------------------------------------------------------
# 3. Helper Functions
# ----------------------------------------------------------------------

def pdf_pages_to_base64_pngs(pdf_path: str, num_pages: int = 3) -> List[str]:
    """
    Converts the first `num_pages` of a PDF to a list of Base64 encoded PNG strings.
    """
    base64_images = []
    try:
        doc = fitz.open(pdf_path)
        count = min(doc.page_count, num_pages)
        
        for i in range(count):
            page = doc.load_page(i)
            zoom = 2 # Higher resolution for better OCR/Vision
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pix.tobytes("png")
            base64_string = base64.b64encode(png_bytes).decode('utf-8')
            base64_images.append(base64_string)
            
        doc.close()
        return base64_images

    except Exception as e:
        print(f"[red]Error converting PDF pages to images: {e}[/red]")
        return []

# --- Model Rotation ---
ROTATIONAL_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

ROTATIONAL_KEYS = [
    "AIzaSyCCxAJreoRXH1jYaq0dPhlzk52opMYHPM0",
    "AIzaSyBL9SUn4aXvvxc8OqZzIzvcBUkJ8sRSxek",
    "AIzaSyBw_notbid5jAsdi8FSEsIHWRt68S_VvIw",
    "AIzaSyDiOzB5GWedkNt520JDHUpBTzAVfeiRh8g",
    "AIzaSyD1o1uoDv0-SkSoPtgjvDNF90jt9f2Ln9o",
    "AIzaSyD1rccazE8VB2IMsq8y_H52kMIsKbtp4j0",
]
model_cycler = itertools.cycle(ROTATIONAL_MODELS)
key_cycler = itertools.cycle(ROTATIONAL_KEYS)

def get_extraction_model_client():
    """Get a rotational LLM client for extraction tasks."""
    print("Waiting 2 seconds before getting extraction model client...")
    time.sleep(2) 
    model_name = next(model_cycler)
    api_key = next(key_cycler)
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        max_retries=2,
        google_api_key=api_key
    )

def extract_citation_fields(pdf_path: str) -> Optional[DocumentMetadata]:
    """
    Extracts metadata from a PDF by analyzing its first few pages using a multimodal LLM.
    """
    if not pdf_path or not Path(pdf_path).exists():
        print(f"[red]PDF path does not exist: {pdf_path}[/red]")
        return None

    print(f"[blue]Extracting metadata from: {Path(pdf_path).name}[/blue]")
    
    # 1. Get images of the first 3 pages
    images = pdf_pages_to_base64_pngs(pdf_path, num_pages=3)
    if not images:
        return None

    # 2. Prepare the message for the LLM
    content_parts = [{"type": "text", "text": unified_metadata_extract_prompt}]
    for img in images:
        content_parts.append({"type": "image_url", "image_url": f"data:image/png;base64,{img}"})

    message = HumanMessage(content=content_parts)

    # 3. Invoke the LLM
    llm = get_extraction_model_client()
    structured_llm = llm.with_structured_output(DocumentMetadata, method="json_mode")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = structured_llm.invoke([message])
            if result:
                print(f"[green]Successfully extracted metadata for {Path(pdf_path).name}[/green]")
                return result
        except Exception as e:
            print(f"[yellow]Attempt {attempt+1} failed: {e}[/yellow]")
            time.sleep(2)
    
    print("[red]Failed to extract metadata after retries.[/red]")
    return None

def process_metadata(documents: List, pdf_path: str) -> List:
    """
    Applies extracted metadata to a list of document chunks.
    This function now expects `extract_citation_fields` to have been called *before* 
    or calls it once here if not provided (though the new architecture prefers calling it once per file).
    
    For backward compatibility and ease of integration, we will call extract_citation_fields here 
    if the documents don't already have rich metadata, but ideally, we do it once per file.
    """
    if not documents:
        return []

    # Extract metadata ONCE for the file
    metadata = extract_citation_fields(pdf_path)
    
    processed_docs = []
    for doc in documents:
        # Start with existing metadata (like source, full_path)
        new_metadata = doc.metadata.copy()
        
        if metadata:
            # Update with LLM-extracted fields
            new_metadata.update({
                "title": metadata.title,
                "author": metadata.author,
                "year": metadata.year,
                "publisher": metadata.publisher,
                "journal_title": metadata.journal_title,
                "volume": metadata.volume,
                "issue": metadata.issue,
                "page_range": metadata.page_range,
                "doi_url": metadata.doi_url,
                "edition": metadata.edition,
                "place": metadata.place,
                "document_type": metadata.document_type
            })
        else:
            # Fallback defaults if extraction failed
            new_metadata.update({
                "title": new_metadata.get("source", "N/A"),
                "author": "N/A",
                "year": "N/A"
            })
            
        processed_docs.append(Document(page_content=doc.page_content, metadata=new_metadata))

    return processed_docs