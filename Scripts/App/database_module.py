from langchain_huggingface import HuggingFaceEmbeddings
from Scripts.App.database.database import RetrievalTool
from Scripts.App.main import repeatedly_ask
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("--- Setting up environment ---")
# The path should be relative to the project root, not the test script location
os.makedirs("./database/data/uploads/code", exist_ok=True)
os.makedirs("./database/data/uploads/docs", exist_ok=True)
def add_documents_to_db(retrieval_tool: RetrievalTool):
    while True:
        print("Let's add documents to your database.")
        user_path = repeatedly_ask("Enter your path to your documents separated by comma (,) ")
        user_paths = [path.strip().replace("\\", "/") for path in user_path.split(",") if Path(path.strip()).is_dir() or Path(path.strip()).is_file()]
        if not user_paths:
            print("No valid paths provided. Please try again.")
            continue
        else:
            for indx, path in enumerate(user_paths):
                print(f"Path {indx+1}: {path}")
            break

    print(f"Database path: {retrieval_tool.db_path}")
    print(f"Collections: {retrieval_tool.list_collections()}")

    print("\n--- Processing documents ---")
    retrieval_tool.process_documents(
        file_paths=user_paths,#["./uploads"], # This path is now correct relative to project root
        chunk_size=10000,
        chunk_overlap=500 ,
        
    )
if __name__ == "__main__":
    retrieval_tool = RetrievalTool(db_path="./database/data/db")
    print("\n--- Performing an MMR query ---")
    mmr_results = retrieval_tool.query_with_mmr(
        query_text="Explain external foreign strategies like licensing and direct investment",
    )
    if mmr_results:
        print("MMR Query Results (SHOULD NOW WORK):")
        for doc in mmr_results:
            page_text = doc.page_content[:1500].replace('\n', ' ')
            print(f"  - (Source: {doc.metadata['source']}) {page_text}...")
    else:
        print("MMR Query Failed.")