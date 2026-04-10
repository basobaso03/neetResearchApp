import logging
from typing import List, Dict, Any, Optional
import asyncio
from langchain_core.tools import tool
from Scripts.App.database.database import RetrievalTool
from Scripts.App.tools.web_search_tool import summarize_content
from rich import print

class GraphTools:
    """
    A collection of tools for interacting with the document retrieval system.
    """
    def __init__(self, retrieval_tool: RetrievalTool):
        self.retrieval_tool = retrieval_tool
        self.metadata_to_include =["source","title","creationdate","producer", "page","page_label"]


    #@tool
    async def similarity_search(self, query: str) -> str:
        """
        Use this tool to find the most specific, focused, and top-ranked documents
        for a direct question. It's best for getting the most relevant answer quickly.
        """
        logging.info(f"Performing similarity search for query: '{query}'")
        print(f"Performing similarity search for query: '{query}'")

        docs =  self.retrieval_tool.query( query_text=query)
        #print(f"Docs: {docs}")
        
        if not docs:
            return "No relevant documents found in the database."
        data = [f"---Context ---> {document} --- METADATA----> {metadata}" for document, metadata in zip(docs["documents"][0],docs["metadatas"][0])]

        for sc in data:
            print(f"SC: {sc}")


        # Concurrently summarize all retrieved documents
        summarization_tasks = [summarize_content(data, query, is_database=True) for doc in docs]
        summaries = await asyncio.gather(*summarization_tasks)

        # Format the final output string for the agent
        formatted_results = []
        for i, summary in enumerate(summaries):
            print(summary.metadata)
            print(f"Metadata Type: {type(summary.metadata)}")
            # allowed_metadata = {k: v for k, v in summary.metadata.items() if k in self.metadata_to_include}
            # summary.metadata = allowed_metadata  # Update metadata to only include allowed fields
            # print(f"======================================================= Summary {i+1} =================================================================")
            # print(f"Summary: {summary.summary} \n")
            # print(f"Key Excerpts: {summary.key_excerpts} \n")
            # print(f"Metadata: {summary.metadata} \n")
            # print("=========================================================================================================================================")

            source_str = (
                f"--- SOURCE {i+1} ---\n"
                #f"SOURCE FILE: {summary.metadata.get('source', 'N/A')}\n"
                f"SUMMARY:\n{summary.summary}\n\n"
                f"KEY EXCERPTS:\n{summary.key_excerpts}\n\n"
                f"CITATION INFO: {summary.metadata}\n" # Include all metadata for citation
                "--------------------"
            )
            formatted_results.append(source_str)

        return "\n\n".join(formatted_results)


    #@tool
    async def diverse_search(self, query: str) -> str:
        """
        Use this tool for broader research questions to get a diverse set of documents
        covering multiple aspects of a topic, while actively avoiding redundant information.
        """
        logging.info(f"Performing diverse (MMR) search for query: '{query}'")
        print(f"Performing diverse (MMR) search for query: '{query}'")

        docs =  self.retrieval_tool.query_with_mmr( query_text=query)
        #print(f"Docs: {docs}")
        if not docs:
            return "No relevant documents found in the database."
        data = [f"---Context ---> {document.page_content} --- METADATA----> {document.metadata}" for document in docs]
        
        # Concurrently summarize all retrieved documents
        summarization_tasks = [summarize_content(data, query, is_database=True) for doc in docs]
        summaries = await asyncio.gather(*summarization_tasks)
        
        # Format the final output string for the agent
        
        formatted_results = []
        for i, summary in enumerate(summaries):
            print(summary.metadata)
            print(f"Metadata Type: {type(summary.metadata)}")
            # allowed_metadata = {k: v for k, v in summary.metadata.items() if k in self.metadata_to_include}
            # summary.metadata = allowed_metadata  # Update metadata to only include allowed fields
            # print(f"======================================================= Summary {i+1} =================================================================")
            # print(f"Summary: {summary.summary} \n")
            # print(f"Key Excerpts: {summary.key_excerpts} \n")
            # print(f"Metadata: {summary.metadata} \n")
            # print("=========================================================================================================================================")
            source_str = (
                f"--- SOURCE {i+1} ---\n"
            # f"SOURCE FILE: {summary.metadata.get('source', 'N/A')}\n"
                f"SUMMARY:\n{summary.summary}\n\n"
                f"KEY EXCERPTS:\n{summary.key_excerpts}\n\n"
                f"CITATION INFO: {summary.metadata}\n" # Include all metadata for citation
                "--------------------"
            )
            formatted_results.append(source_str)

        return "\n\n".join(formatted_results)