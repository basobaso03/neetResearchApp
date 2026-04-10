import os
import logging
import chromadb
from multiprocessing import Pool, cpu_count
from typing import List, Dict, Optional, Any
from rich import print
import rich
from Scripts.App.database.extract_pdf_text import PDFTextExtractor
from Scripts.App.database.db_helpers import process_metadata
import re

# --- Langchain Document Loader Imports ---
from langchain_community.document_loaders import (
    Docx2txtLoader,
    UnstructuredPowerPointLoader,
    BSHTMLLoader,
    TextLoader,
)
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    Language,
)
from langchain_core.documents import Document

# --- Langchain Vector Store and Embeddings for MMR ---

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from chromadb.utils import embedding_functions
from chromadb.errors import NotFoundError

# --- Setup basic logging for user notifications ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# --- Mapping file extensions to loaders and languages ---
LOADER_MAPPING = {
    ".docx": Docx2txtLoader,
    ".pptx": UnstructuredPowerPointLoader,
    ".html": BSHTMLLoader,
}
PDF_MAPPING = {".pdf": PDFTextExtractor}

LANGUAGE_MAPPING = {
    ".py": Language.PYTHON,
    ".java": Language.JAVA,
    ".md": Language.MARKDOWN,
    ".js": Language.JS,
    ".ts": Language.TS,
    ".html": Language.HTML,
}

# --- Worker function for multiprocessing ---
def load_and_split_file(
    file_path: str,
    chunk_size: int,
    chunk_overlap: int
) -> Optional[List[Document]]:
    """
    Loads a single file, splits it into chunks, and adds metadata.
    Returns a list of Document chunks or None if the file is unsupported.
    """
    try:
        ext = os.path.splitext(file_path)[1].lower()
        file_name = os.path.basename(file_path)
        logging.info(f"Processing file: {file_name}")
        text_splitter=None

        docs: List[Document] = []

        if ext in LOADER_MAPPING:
            loader = LOADER_MAPPING[ext](file_path)
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif ext in LANGUAGE_MAPPING:
            language = LANGUAGE_MAPPING[ext]
            loader = TextLoader(file_path, encoding="utf-8")
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter.from_language(
                language=language,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif ext in PDF_MAPPING:
            pdf_extractor = PDF_MAPPING[ext]()
            docs = pdf_extractor.extract_and_chunk(
                file_path,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
           
        else:
            logging.warning(f"Unsupported file type: {file_name}. Skipping.")
            return None

        # extract metadata from the first page if journal
        if text_splitter is None:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        
        if docs:
            chunks = text_splitter.split_documents(docs)
            for chunk in chunks:
                chunk.metadata["source"] = file_name
                chunk.metadata['full_path'] = file_path
            
            # Process metadata using the robust LLM-based approach
            split_chunks = process_metadata(chunks, pdf_path=file_path)
            return split_chunks
            
        return None

    except Exception as e:
        logging.error(f"Error processing file {file_path}: {e}")
        return None


class RetrievalTool:
    """
    A tool for creating and managing a document retrieval system
    optimized for large vector storage using ChromaDB.
    """
    def __init__(self, db_path: str="./data/db"):
        """
        Initializes the RetrievalTool.

        Args:
            db_path (str): The file system path to persist the ChromaDB database.
        """
        if not os.path.exists(db_path):
            os.makedirs(db_path)
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=self.db_path)

        self.embedding_function = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        self.chroma_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        self._vector_store_cache: Dict[str, Chroma] = {}
        logging.info(f"RetrievalTool initialized with database at: {self.db_path}")

        self.collection_name =None

    def set_collection_name(self,collection_name:str):
        collections = self.list_collections()
        if collection_name not in collections and collection_name is not None and len(collection_name.strip())>0:
            print(f"Collection '{collection_name}' does not exist. It will be created.")
            self.client.create_collection(name=collection_name,embedding_function=self.chroma_ef)
            self.collection_name =collection_name
            print(f"Created and set collection name to: {self.collection_name}")

        elif collection_name in collections and collection_name is not None and len(collection_name.strip())>0:
            self.collection_name =collection_name
            print(f"Set collection name to: {self.collection_name}")
        else:
            raise ValueError("Collection name cannot be empty or None.")

    def process_documents(
        self,
        file_paths: List[str]= ['./database/data/uploads/docs'],
        chunk_size: int = 5000,
        chunk_overlap: int = 500,
    ):
        """
        Processes a list of file and directory paths, vectorizes their content,
        and stores them in a specified ChromaDB collection.
        """
        logging.info("Starting to load documents...")

        # chroma_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        #     model_name="all-MiniLM-L6-v2"
        # )
        collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.chroma_ef
        )

        all_files_to_process = []
        for path in file_paths:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        all_files_to_process.append(os.path.join(root, file))
            elif os.path.isfile(path):
                all_files_to_process.append(path)

        all_chunks = []
        worker_args = [(path, chunk_size, chunk_overlap) for path in all_files_to_process]

        with Pool(processes=max(1, cpu_count() - 1)) as pool:
            results = pool.starmap(load_and_split_file, worker_args)
            for result in results:
                if result:
                    all_chunks.extend(result)

        if not all_chunks:
            logging.warning("No documents were processed or all files were unsupported.")
            return

        logging.info(
            f"Converting {len(all_chunks)} document chunks to vectors "
            f"and storing in collection '{self.collection_name}'..."
        )

        documents = [chunk.page_content for chunk in all_chunks]
        metadatas = [chunk.metadata for chunk in all_chunks]
        ids = [f"{hash(meta['full_path'])}_{i}" for i, meta in enumerate(metadatas)]

        batch_size = 1000
        for i in range(0, len(documents), batch_size):
            collection.add(
                ids=ids[i:i + batch_size],
                documents=documents[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size],
            )

        logging.info("Vectorization complete. The tool is ready for retrieval.")

    def list_collections(self) -> List[str]:
        """Lists all available collections in the database."""
        return [collection.name for collection in self.client.list_collections()]

    def list_documents(self, collection_name: str) -> List[str]:
        """Lists the unique source document names within a specific collection."""
        try:
            collection = self.client.get_collection(name=collection_name)
            results = collection.get(include=["metadatas"])
            if not results or not results['metadatas']:
                return []
            sources = {metadata['source'] for metadata in results['metadatas'] if 'source' in metadata}
            return sorted(list(sources))
        except ValueError:
            logging.error(f"Collection '{collection_name}' not found.")
            return []

    def delete_collection(self, collection_name: str):
        """Deletes an entire collection from the database."""
        try:
            self.client.delete_collection(name=collection_name)
            logging.info(f"Collection '{collection_name}' deleted successfully.")
        except ValueError:
            logging.error(f"Collection '{collection_name}' not found.")

    def delete_documents(self, collection_name: str, document_names: List[str]):
        """Removes all vector chunks associated with specific source document names."""
        try:
            collection = self.client.get_collection(name=collection_name)
            collection.delete(where={"source": {"$in": document_names}})
            logging.info(f"Documents {document_names} deleted from collection '{collection_name}'.")
        except ValueError:
            logging.error(f"Collection '{collection_name}' not found.")
        except Exception as e:
            logging.error(f"An error occurred while deleting documents: {e}")

    def query(
        self,
        query_text: str,
        n_results: int = 3,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, List[Any]]]:
        """Performs a similarity search query against a collection."""
        try:
            collection = self.client.get_collection(name=self.collection_name)
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=filter_metadata,
            )
            return results
        except NotFoundError:
            logging.error(f"Collection '{self.collection_name}' not found.")
            return None
        except Exception as e:
            logging.error(f"An error occurred during query: {e}")
            return None

    def query_with_mmr(
        self,
        query_text: str,
        k: int = 3,
        fetch_k: int = 20,
    ) -> Optional[List[Document]]:
        """Performs a query using Maximum Marginal Relevance (MMR) to diversify results."""
        try:
            if self.collection_name not in self._vector_store_cache:

                self._vector_store_cache[self.collection_name] = Chroma(
                    client=self.client,
                    collection_name=self.collection_name,
                    embedding_function=self.embedding_function
                )
            vector_store = self._vector_store_cache[self.collection_name]

            results = vector_store.max_marginal_relevance_search(
                query=query_text, k=k, fetch_k=fetch_k
            )
            return results
        except NotFoundError:
            logging.error(f"Collection '{self.collection_name}' not found.")
            return None
        except Exception as e:
            logging.error(f"An error occurred during MMR query: {e}")
            return None