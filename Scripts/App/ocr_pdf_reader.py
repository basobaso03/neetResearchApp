# import os
# from langchain_community.document_loaders import PyMuPDFLoader
# from typing import List

# def extract_text_from_pdf(pdf_path: str) -> str:
#     """
#     Extracts text from a PDF file, including both selectable text and
#     text from images using OCR.

#     Args:
#         pdf_path: The file path to the PDF document.

#     Returns:
#         A string containing all the extracted text.
#         Returns an error message if the file is not found.
#     """
#     if not os.path.exists(pdf_path):
#         return f"Error: File not found at {pdf_path}"

#     # The extract_images=True parameter enables OCR for images in the PDF.
#     # PyMuPDFLoader will automatically use an available OCR tool like Tesseract.
#     loader = PyMuPDFLoader(pdf_path, extract_images=True)

#     try:
#         documents = loader.load()
        
#         # Combine the content of all loaded pages/documents
#         full_text = "".join(doc.page_content for doc in documents)
        
#         return full_text
#     except Exception as e:
#         return f"An error occurred during PDF processing: {e}"

# # --- Example Usage ---

# # Create a dummy PDF path for the example.
# # In a real scenario, you would replace this with the actual path to your PDF.
# # For example: file_path = "path/to/your/document.pdf"

# print(f"Attempting to extract text from: \n")

# # Call the function to extract text
# extracted_text = extract_text_from_pdf("./FLAT[R22A0510].pdf")

# # Print the result
# print("--- Extracted Text ---")
# print(extracted_text)

# # Clean up the placeholder file
# # os.remove(file_path)

# from PIL import Image
# import pytesseract
# import os

# # --- IMPORTANT: CONFIGURE THIS SECTION ---
# # If you are on Windows, provide the full path to tesseract.exe
# # This is the most common point of failure.
# # Make sure the path is correct for your installation.
# if os.name == 'nt':
#     #pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
#     pass
# # -----------------------------------------

# try:
#     # Open the test image
#     image_path = './test.jpeg'
    
#     img = Image.open(image_path)

#     # Use pytesseract to extract text
#     text = pytesseract.image_to_string(img)

#     print("--- OCR Result ---")
#     if text.strip():
#         print(text)
#     else:
#         print("OCR process ran, but NO TEXT was detected.")
#         print("This could be due to a missing 'tessdata' folder or a low-quality image.")

# except pytesseract.TesseractNotFoundError:
#     print("--- TESSERACT NOT FOUND ERROR ---")
#     print("pytesseract could not find the Tesseract executable.")
#     print("Please ensure Tesseract is installed and the path in the script is correct.")
#     print("If it's in your system PATH, you can try removing the 'pytesseract.pytesseract.tesseract_cmd' line.")

# except Exception as e:
#     print(f"An unexpected error occurred: {e}")

# import fitz  # PyMuPDF
# from PIL import Image
# import pytesseract
# import os
# import io

# # --- IMPORTANT: CONFIGURE TESSERACT PATH ---
# # This path is correct based on your successful test. Keep it.

# def extract_full_text_from_pdf(pdf_path: str) -> str:
#     """
#     Robustly extracts text from a PDF, including scanned images,
#     by rendering each page as an image and performing OCR.

#     Args:
#         pdf_path: The file path to the PDF document.

#     Returns:
#         A string containing all the extracted text.
#     """
#     if not os.path.exists(pdf_path):
#         return f"Error: File not found at {pdf_path}"

#     print(f"Starting robust extraction for: {pdf_path}")
#     doc = fitz.open(pdf_path)
#     full_text = []

#     # Iterate over each page
#     for page_num in range(len(doc)):
#         page = doc.load_page(page_num)
#         print(f"Processing page {page_num + 1}/{len(doc)}...")

#         # 1. Render page to a high-resolution image (pixmap)
#         # The dpi (dots per inch) can be increased for better quality
#         pix = page.get_pixmap(dpi=300)

#         # 2. Convert the pixmap to a PIL Image
#         # get_pixmap returns raw image data, we need to wrap it
#         img_data = pix.tobytes("png")
#         image = Image.open(io.BytesIO(img_data))
        
#         # 3. Use pytesseract to OCR the image
#         # We also specify English language for better accuracy
#         try:
#             text = pytesseract.image_to_string(image, lang='eng')
#             full_text.append(text)
#         except Exception as e:
#             print(f"  - Error processing page {page_num + 1}: {e}")
            
#     doc.close()
#     print("Extraction complete.")
#     return "\n".join(full_text)


# # --- Example Usage ---
# pdf_file = "your_mixed_content_document.pdf"  # <--- Change to your PDF's name
# extracted_text = extract_full_text_from_pdf("./FLAT[R22A0510].pdf")

# print("\n\n--- FINAL EXTRACTED TEXT ---")
# print(extracted_text)

# import fitz  # PyMuPDF
# from PIL import Image
# import pytesseract
# import os
# import io

# # --- Configure Tesseract Path ---
# # if os.name == 'nt':
# #     pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# # --------------------------------

# def extract_hybrid_text_from_pdf(pdf_path: str) -> str:
#     """
#     Extracts text from a PDF using a hybrid strategy:
#     1. Tries direct text extraction first (fast and accurate).
#     2. If a page yields little text, it falls back to OCR (robust but slower).
#     """
#     if not os.path.exists(pdf_path):
#         return f"Error: File not found at {pdf_path}"

#     print(f"Starting hybrid extraction for: {pdf_path}")
#     doc = fitz.open(pdf_path)
#     full_text = []
    
#     # A threshold to decide if a page is likely image-based
#     # If direct text extraction yields fewer characters than this, we use OCR.
#     TEXT_LENGTH_THRESHOLD = 100 

#     for page_num in range(len(doc)):
#         page = doc.load_page(page_num)
#         print(f"Processing page {page_num + 1}/{len(doc)}...")

#         # --- Strategy 1: Attempt Direct Text Extraction ---
#         direct_text = page.get_text("text")

#         if len(direct_text.strip()) > TEXT_LENGTH_THRESHOLD:
#             print("  - Success: Used direct text extraction.")
#             full_text.append(direct_text)
#         else:
#             # --- Strategy 2: Fallback to OCR ---
#             print("  - Fallback: Using OCR, as direct extraction yielded little text.")
#             try:
#                 pix = page.get_pixmap(dpi=300)
#                 img_data = pix.tobytes("png")
#                 image = Image.open(io.BytesIO(img_data))
                
#                 ocr_text = pytesseract.image_to_string(image, lang='eng')
#                 full_text.append(ocr_text)
#             except Exception as e:
#                 print(f"    - OCR Error on page {page_num + 1}: {e}")

#     doc.close()
#     print("Extraction complete.")
#     return "\n".join(full_text)


# # --- Example Usage ---
# pdf_file = "your_mixed_content_document.pdf"  # <--- Your PDF name
# extracted_text = extract_hybrid_text_from_pdf("./FLAT[R22A0510].pdf")

# print("\n\n--- FINAL HYBRID EXTRACTED TEXT ---")
# print(extracted_text)

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
                Example: r'C:\Program Files\Tesseract-OCR\tesseract.exe'
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