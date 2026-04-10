# NeetResearch App System Overview

## Short Description

This system is an AI-powered research application that combines a web frontend, a FastAPI backend, and a graph-based agent workflow.

In simple terms, the user submits a research topic, the backend routes that request through specialized agents and tools, and the system returns a structured final report.

## Technical Description

The application is built with three main layers:

- **Frontend**: React + TypeScript UI that starts research sessions, shows progress, and displays final reports.
- **Backend API**: FastAPI service that manages sessions, progress updates, exports, and WebSocket communication.
- **Agent workflow**: LangGraph and Google ADK-based orchestration that coordinates scoping, supervision, research, and report generation.

Key backend files:

- [Scripts/App/api/main.py](Scripts/App/api/main.py)
- [Scripts/App/api/routes/research.py](Scripts/App/api/routes/research.py)
- [Scripts/App/graph/graph.py](Scripts/App/graph/graph.py)
- [Scripts/App/graph/deep_research_graph.py](Scripts/App/graph/deep_research_graph.py)
- [Scripts/App/graph/agents/supervisor_agent.py](Scripts/App/graph/agents/supervisor_agent.py)
- [Scripts/App/graph/agents/research_agent.py](Scripts/App/graph/agents/research_agent.py)
- [Scripts/App/tools/web_search_tool.py](Scripts/App/tools/web_search_tool.py)
- [Scripts/App/tools/adk_db_search.py](Scripts/App/tools/adk_db_search.py)

Frontend files that drive the user experience:

- [frontend/src/services/api.ts](frontend/src/services/api.ts)
- [frontend/src/hooks/useInitialization.ts](frontend/src/hooks/useInitialization.ts)
- [frontend/src/components/layout/Layout.tsx](frontend/src/components/layout/Layout.tsx)
- [frontend/src/pages/ResearchProgressPage.tsx](frontend/src/pages/ResearchProgressPage.tsx)
- [frontend/src/store/researchStore.ts](frontend/src/store/researchStore.ts)

## Functional Description

From the user’s perspective, the system does the following:

1. The user enters a topic or query.
2. The frontend sends the request to the backend.
3. The backend creates a session and starts a background research task.
4. The UI shows initialization and research progress.
5. Specialized agents gather information from the web or database.
6. The system synthesizes the findings into a final report.
7. The user can view, resume, cancel, or export the report.

The app supports both:

- **Web research**: searches the internet and summarizes relevant sources.
- **Database research**: searches the local ChromaDB-backed document store.
- **Deep research**: adds extra analysis and a more comprehensive report generation step.

## Concepts Used

### 1. Agent Orchestration

The app is not a single prompt-response call. It uses multiple agents with different responsibilities.

- **Scoping agent**: clarifies the user request and turns it into a research brief.
- **Supervisor agent**: decides how research should proceed and delegates work.
- **Research agent**: performs the actual research using tools.
- **Report generation step**: combines notes into the final answer.

### 2. Graph-Based Workflow

The system uses LangGraph state graphs to route work through nodes.

This makes the process structured and repeatable:

- start
- scoping
- supervision
- tool execution
- compression
- final report

### 3. Tool Calling

Agents do not only generate text. They can call tools such as:

- web search
- database similarity search
- diverse search
- reflection or thinking tools

This is how the system gathers evidence before writing the report.

### 4. Retrieval-Augmented Generation

For database mode, the system retrieves documents from ChromaDB and uses them as context for the model.

This means the model is answering from stored local knowledge, not only from general model memory.

### 5. Model Rotation

The code uses rotating Gemini models to reduce overload and spread requests across lighter and stronger variants.

This helps with:

- rate-limit handling
- load balancing
- faster response for simpler tasks
- better performance on complex tasks

### 6. Asynchronous Processing

Research is started in the background while the UI stays responsive.

Progress is delivered using WebSockets and polling endpoints, so the frontend can show live updates.

## Communication Flow

### User to Final Report

```text
User input
  -> Frontend form
  -> API request to FastAPI backend
  -> Session created
  -> Initialization progress sent to UI
  -> Scoping agent creates research brief
  -> Supervisor agent routes tasks
  -> Research agent uses web/database tools
  -> Notes collected and compressed
  -> Final report generated
  -> Report returned to frontend
  -> User views or exports report
```

### Backend Communication Pattern

- The frontend talks to the backend through HTTP endpoints in [frontend/src/services/api.ts](frontend/src/services/api.ts).
- The frontend watches startup readiness through `/api/init-status` and `/ws/init`.
- Research progress is pushed through `/ws/research/{session_id}`.
- The backend stores session state in memory and returns status updates through API endpoints.

## A Good Technical Way to Describe It

If you need a concise technical explanation for someone else, you can say:

> This is a graph-orchestrated AI research system. The frontend submits a research request to a FastAPI backend, which routes the task through specialized agent nodes for scoping, supervision, retrieval, and summarization. The agents use web search, database retrieval, and Gemini model calls to gather evidence, then generate a final structured report that is streamed back to the UI through session and WebSocket updates.

## A Simple Non-Technical Version

> The app takes a research topic, breaks it into steps, uses specialized AI agents to collect information, and then turns that into a final report that the user can view and export.

## Notes

- The system is agent-based, not just direct API calling.
- The frontend is only the user interface and communication layer.
- The real logic lives in the backend graph and agent workflow.
- Progress reporting is built in, so the user can see the system working while the report is being created.
