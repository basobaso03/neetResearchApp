# # %%
# import nest_asyncio
# nest_asyncio.apply()

import sys
import os
from dotenv import load_dotenv
from rich.markdown import Markdown
from rich import print
from langchain_core.messages import HumanMessage
import asyncio
from langchain_huggingface import HuggingFaceEmbeddings
from Scripts.App.database.database import RetrievalTool
from Scripts.App.export.export_report import ExportReport, Font, smart_export, free_export
from prompt_toolkit import prompt

# Import new utilities
from Scripts.App.utils import (
    validate_topic,
    get_research_logger,
)

#sys.path.append(os.path.abspath(os.path.join('..', 'src')))
load_dotenv()

# %%
from graph.graph import NeetResearchAppGraph

# %%
# This is our final test case. We provide a clear, complex request
# that will flow through the entire system without needing clarification.


def repeatedly_ask(variable_name=None,is_multiline=False):
    while True:
        if is_multiline:
            try:
                user_input = prompt(f"{variable_name} (or type 'exit' to quit): ", multiline=True)
            except Exception:
                # Fallback to standard input if prompt_toolkit fails (e.g. no console)
                print("[yellow]Warning: Multi-line input not supported in this environment. Using standard input.[/yellow]")
                user_input = input(f"{variable_name} (or type 'exit' to quit): ")
        else:
            user_input = input(f"{variable_name} (or type 'exit' to quit): ")
        if user_input.lower().strip() == 'exit':
            print("Exiting the Neet Research App. Goodbye!")
            sys.exit(0)
        if user_input.strip():
            return user_input
        else:
            print(f"The value for {variable_name} cannot be empty. Please try again.")

def NeetResearchApp(db_tools:RetrievalTool, neet_research_app:NeetResearchAppGraph):
    from Scripts.App.database_module import add_documents_to_db
    while True:
        user_request = repeatedly_ask("What do you want to research about today?", is_multiline=True)
        if user_request.lower().strip() == 'exit':
            print("Exiting the Neet Research App. Goodbye!")
            break
        # %%
        # Validate and sanitize user input
        logger = get_research_logger()
        is_valid, cleaned_topic, errors = validate_topic(user_request)
        if not is_valid:
            print(f"[red]Invalid input: {errors}[/red]")
            continue
        user_request = cleaned_topic
        logger.info(f"Research topic: {user_request[:50]}...")
        
        # %%
        # We wrap the user's request in the AgentState format.
        valid =False
        is_research_web=True
        while not valid:

            need_web_research = input("Answer this Question using:\n1. Web Search \n2. Database\n>>> ")
            if need_web_research and 0<len(need_web_research.strip())<2 and need_web_research.isdigit() and 0<int(need_web_research)<3:
                valid=True
                if int(need_web_research)==1:
                    print("Using web research......")
                    is_research_web=True
                else:
                    print("Using your Database......")
                    print(f"Db path: {db_tools.db_path}")
                    print(f"Collections: {db_tools.list_collections()}")
                    collections = db_tools.list_collections()
                    if collections and len(collections)>0:
                        print(f"Found {len(collections)} collections in the database.")
                        for idx, col in enumerate(collections):
                            print(f"Collection {idx + 1}: {col}")
                        print("C: Create a new collection?")
                        print("Please choose a collection by entering the corresponding number.")

                        while True:
                            user_index = repeatedly_ask("Enter the collection number: ")
                            try:
                                if user_index.isdigit() and 0<int(user_index)<=len(collections):
                                    chosen_collection = collections[int(user_index)-1]
                                    db_tools.set_collection_name(chosen_collection)
                                    print(f"Using collection: {chosen_collection}")
                                    is_research_web=False
                                    break
                                elif user_index.strip().lower()=='c':
                                    collection_name = repeatedly_ask("Enter the new collection name: ")
                                    db_tools.set_collection_name(collection_name)
                                    print(f"Using collection: {collection_name}")
                                    add_documents_to_db(db_tools)
                                    is_research_web=False
                                    break
                                else:
                                    print("Invalid input. Please enter a valid collection number.")
                                    continue
                            except ValueError:
                                print("Invalid input. Please Enter valid input.")
                                continue
                    else:
                        try:
                            print("No collections found in the database. Either create one or use web research.")
                            user_decision = input("Do you want to create a new collection? (yes/no): ").strip().lower()
                            if user_decision == 'yes':
                                collection_name = repeatedly_ask("Enter the new collection name: ")
                                db_tools.set_collection_name(collection_name)
                                is_research_web=False
                            elif user_decision == 'no':
                                print("Switching to web research...")
                                is_research_web=True
                            else:
                                print("Invalid input. Please enter 'yes' or 'no'.")
                                continue
                        
                        except ValueError:
                            print("Invalid input. Please Enter valid input.")
                            continue

        initial_state = {"messages": [HumanMessage(content=user_request)], "is_research_web":is_research_web}

        # %%
        # Invoke the full application. This will take several minutes.
        # It will run scoping -> supervision (with parallel workers) -> report generation.
        final_state = asyncio.run(neet_research_app.ainvoke(initial_state))

        # %%
        # Print the final report from the application's state.
        print(Markdown(final_state['final_report']))
        print("\n\n"+f"is web_search used: { final_state['is_research_web']}")



        print("------------------------------------------------ Export Report ------------------------------------------------")
        print("Export options:")
        print("1. Markdown (FREE - no API usage)")
        print("2. PDF (uses API credits)")
        print("3. Skip export")
        
        export_choice = input("Choose export format (1/2/3): ").strip()
        
        if export_choice == "1":
            # FREE markdown export
            file_name = repeatedly_ask("Enter the file name: ", is_multiline=False)
            result = free_export(final_state['final_report'], file_name)
            print(f"✅ Report saved to: {result}")
        elif export_choice == "2":
            # LLM-based PDF export
            file_name = repeatedly_ask("Enter the file name: ", is_multiline=False)
            result = smart_export(final_state['final_report'], file_name, "pdf", use_llm=True)
            print(f"✅ Report saved to: {result}")
        else:
            print("Report not exported.")
            continue

def main():
    from Scripts.App.database_module import add_documents_to_db
    try:
        print("BASOBASO SOFTWARE....")
        print("-------------------------------- Setting up enviroment --------------------------------")

        db_tools =RetrievalTool(db_path="./database/db")
        print("Done setting up the enviroment....")
        print("-------------------------------- Building the app graph --------------------------------")
        neet_research_app = NeetResearchAppGraph(db_tools).build()
        
        # Build the Deep Research Graph
        from Scripts.App.graph.deep_research_graph import DeepResearchGraph
        deep_research_app = DeepResearchGraph(db_tools).build()
        
        print("Done building the app graph....")
        print("Welcome to Neet Research App!")
        while True:
            print("Choose an option:")
            print("1. Add documents to the database")
            print("2. Start a research session (Standard)")
            print("3. Start a Deep Research session (Comprehensive Analysis)")
            print("4. Exit")
            choice = input("Enter your choice (1/2/3/4): ").strip()
            if choice == '1':
                collections = db_tools.list_collections()
                if collections and len(collections)>0:
                    print(f"Found {len(collections)} collections in the database.")
                    for idx, col in enumerate(collections):
                        print(f"Collection {idx + 1}: {col}")
                    print("C: Create a new collection?")
                    print("Please choose a collection by entering the corresponding number.")

                    while True:
                        user_index = repeatedly_ask("Enter the collection number ")
                        try:
                            if user_index.isdigit() and 0<int(user_index)<=len(collections):
                                chosen_collection = collections[int(user_index)-1]
                                db_tools.set_collection_name(chosen_collection)
                                print(f"Using collection: {chosen_collection}")
                                break
                            elif user_index.strip().lower()=='c':
                                collection_name = repeatedly_ask("Enter the new collection name: ")
                                db_tools.set_collection_name(collection_name)
                                print(f"Using collection: {collection_name}")
                                break
                            else:
                                print("Invalid input. Please enter a valid collection number.")
                                continue
                        except ValueError:
                            print("Invalid input. Please Enter valid input.")
                            continue
                else:
                    print("No collections found in the database. You need to create one.")
                    collection_name = repeatedly_ask("Enter the new collection name: ")
                    db_tools.set_collection_name(collection_name)
                    print(f"Using collection: {collection_name}")
                add_documents_to_db(db_tools)
            elif choice == '2':
                print("Tell me what you want to research about to day.")
                NeetResearchApp(db_tools, neet_research_app)
            elif choice == '3':
                print("[bold magenta]Starting Deep Research Session...[/bold magenta]")
                print("Tell me what you want to research about to day.")
                NeetResearchApp(db_tools, deep_research_app)
            elif choice == '4':
                print("Exiting the Neet Research App. Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")
    except KeyboardInterrupt:
        print("\nExiting the Neet Research App. Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
        
