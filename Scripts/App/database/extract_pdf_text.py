
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import os
import io
from typing import List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

class PDFTextExtractor:
    """
    A class to extract text and metadata from PDF files using a hybrid approach.

    This class first attempts to extract text directly. If a page yields
    insufficient text (indicating a scanned image), it falls back to using
    Tesseract OCR to extract text from a rendered image of the page.
    
    The extracted text is then chunked, and each chunk is enriched with
    metadata from the PDF document.
    """

    def __init__(self, tesseract_cmd_path: Optional[str] = None):
        """
        Initializes the PDFTextExtractor.

        Args:
            tesseract_cmd_path (Optional[str]): The full path to the Tesseract
                executable. If None, it's assumed Tesseract is in the system's PATH.
                This is primarily needed for Windows installations.
                Example: r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
        """
        if tesseract_cmd_path and os.path.exists(tesseract_cmd_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_path
            print(f"Tesseract command path set to: {tesseract_cmd_path}")
        else:
            try:
                # Check if Tesseract is available in the PATH
                pytesseract.get_tesseract_version()
                print("Tesseract found in system PATH.")
            except pytesseract.TesseractNotFoundError:
                print("Warning: Tesseract executable not found in PATH and no custom path provided. OCR will fail.")

    def _extract_pdf_metadata(self, file_path: str) -> dict:
        """Extracts metadata from the PDF document."""
        try:
            with fitz.open(file_path) as doc:
                # The metadata attribute is a dictionary
                metadata = doc.metadata
                # Add the number of pages to the metadata
                metadata['total_pages'] = len(doc)
                return {k: v for k, v in metadata.items() if v}  # Filter out None values
        except Exception as e:
            print(f"Error extracting metadata from {file_path}: {e}")
            return {}

    def _extract_hybrid_text(self, file_path: str) -> str:
        """
        Extracts text from a PDF using a hybrid of direct extraction and OCR.
        """
        full_text = []
        TEXT_LENGTH_THRESHOLD = 100  # Threshold to decide if OCR is needed

        try:
            with fitz.open(file_path) as doc:
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    
                    # Strategy 1: Attempt direct text extraction
                    direct_text = page.get_text("text")

                    if len(direct_text.strip()) > TEXT_LENGTH_THRESHOLD:
                        full_text.append(direct_text)
                    else:
                        # Strategy 2: Fallback to OCR
                        try:
                            pix = page.get_pixmap(dpi=300)
                            img_data = pix.tobytes("png")
                            image = Image.open(io.BytesIO(img_data))
                            ocr_text = pytesseract.image_to_string(image, lang='eng')
                            full_text.append(ocr_text)
                        except Exception as ocr_error:
                            print(f"  - OCR Error on page {page_num + 1}: {ocr_error}")

        except Exception as e:
            print(f"Error during hybrid text extraction from {file_path}: {e}")
            return ""

        return "\n".join(full_text)

    def extract_and_chunk(self, file_path: str, chunk_size: int=10000, chunk_overlap: int=700) -> List[Document]:
        """
        The main method to orchestrate text extraction, metadata gathering, and chunking.

        Args:
            file_path (str): The path to the PDF file.
            chunk_size (int): The desired size of each text chunk.
            chunk_overlap (int): The overlap between consecutive chunks.

        Returns:
            List[Document]: A list of LangChain Document objects, where each
                            document is a chunk of text with associated metadata.
        """
        if not os.path.exists(file_path):
            print(f"Error: File not found at {file_path}")
            return []

        print(f"--- Processing {os.path.basename(file_path)} ---")
        
        # 1. Extract metadata from the PDF
        metadata = self._extract_pdf_metadata(file_path)
        metadata['source'] = os.path.basename(file_path) # Add source filename

        # 2. Extract the full text using the hybrid method
        print("Extracting text using hybrid strategy...")
        full_text = self._extract_hybrid_text(file_path)
        
        if not full_text.strip():
            print("Warning: No text was extracted from the document.")
            return []
            
        print("Text extraction complete.")

        # 3. Chunk the extracted text using RecursiveCharacterTextSplitter
        print(f"Chunking text with size={chunk_size} and overlap={chunk_overlap}...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            add_start_index=True,
        )
        
        text_chunks = text_splitter.split_text(full_text)
        
        # 4. Create LangChain Document objects for each chunk with combined metadata
        documents = []
        for i, chunk in enumerate(text_chunks):
            # Create a copy of the base metadata and add chunk-specific info
            chunk_metadata = metadata.copy()
            chunk_metadata['chunk_number'] = i + 1
            chunk_metadata['full_path'] = file_path
            doc = Document(page_content=chunk, metadata=chunk_metadata)
            documents.append(doc)

        print(f"Successfully created {len(documents)} chunks.")
        return documents


if __name__ == '__main__':
    # --- EXAMPLE USAGE ---

    # IMPORTANT: Replace this with the actual path to your PDF file.
    # The example will fail if this file doesn't exist.
    PDF_FILE_PATH = "./FLAT[R22A0510].pdf"

    # For Windows users, if Tesseract is not in your PATH, provide the path here.
    # For macOS/Linux users, you can often leave this as None.
    #TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    # Ideal chunking settings for deep research agents
    CHUNK_SIZE = 10000
    CHUNK_OVERLAP = 700

    if not os.path.exists(PDF_FILE_PATH):
        print(f"Error: The example file '{PDF_FILE_PATH}' was not found.")
        print("Please update the 'PDF_FILE_PATH' variable with the path to your PDF.")
    else:
        # 1. Instantiate the extractor
        extractor = PDFTextExtractor()
        
        # 2. Call the main method to get the list of documents
        langchain_documents = extractor.extract_and_chunk(
            file_path=PDF_FILE_PATH,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )

        # 3. Inspect the results
        if langchain_documents:
            print(f"\n--- Inspection of the first document chunk ---")
            print(langchain_documents[0].page_content)
            
            print("\n--- Metadata of the first chunk ---")
            print(langchain_documents[0].metadata)
            
            # Now, `langchain_documents` is ready to be embedded and
            # stored in your vector database.