# CrisisPilot

CrisisPilot is a Slack-native autonomous multi-agent operations platform. It enables incident management, operations tracking, and autonomous mission execution directly within Slack, powered by Large Language Models (LLMs).

## Project Overview

CrisisPilot integrates deeply with Slack, using autonomous agents to evaluate situations, monitor watchlists, and recommend or execute strategic missions. The platform uses a FastAPI backend with a SQLite database, leveraging LangGraph, the Model Context Protocol (MCP), and Groq's LLMs for intelligent, automated assistance.

## Key Features

- **Incident Management**: Track and manage incidents directly from Slack, with state transitions and assignment capabilities.
- **Operations & Missions**: Organize multiple incidents into broader operations and execute missions via autonomous agents.
- **Mini-Agents & Orchestration**: A central `SupervisorAgent` orchestrates domain-specific mini-agents (e.g., News, Weather, Inventory) based on real-time needs.
- **Watchlist Monitoring**: Background jobs continuously monitor news and specific domains (e.g., Global Weather Alerts, Humanitarian Crises).
- **Recommendation Engine**: Domain-specific recommendations for cybersecurity, environmental, humanitarian, infrastructure, natural disasters, public health, transportation, and weather incidents.
- **Timeline & Evidence Subsystem**: Keeps a chronological record of events and stores associated evidence.
- **Slack Integration**: Actionable Slack blocks, interactive modals (`global_update_status`), and slash commands (`/crisispilot-ping`).
- **Model Context Protocol (MCP)**: Supports tools like `WeatherTool`, `NewsTool`, `MapsTool`, and `InventoryTool` for agents to dynamically fetch context.

## Tech Stack

- **Backend Framework**: FastAPI (Python >= 3.11)
- **Slack Integration**: Slack Bolt for Python (`slack-bolt`)
- **Database**: SQLite (Async) via `aiosqlite` and `sqlalchemy[asyncio]`
- **AI / LLM Engine**: Groq API (`llama-3.3-70b-versatile` by default), LangGraph, OpenAI SDK
- **Background Tasks**: `apscheduler`
- **Validation**: Pydantic & Pydantic Settings
- **Testing & Quality**: Pytest, Pytest-Asyncio, Pytest-Cov, Ruff, Mypy

## Project Structure

- `app/`: Contains the main FastAPI application entry point (`main.py`) and Slack routing setup (`slack_setup.py`).
- `core/`: Core abstractions, configuration (`config.py`), notifications, state management (`state.py`), and orchestration (`AgentRegistry`, `SupervisorAgent`).
- `features/`: The main domain logic. Contains modules for analytics, evidence, incident management, mini-agents, missions, monitoring, operations, recommendations, timeline, watchlists, and workflows.
- `infrastructure/`: Database connections (`database.py`), LLM provider implementations (`groq_provider.py`), MCP tool definitions, and Slack integration bootstrapping.
- `storage/`: Local storage directory (holds the SQLite database file).
- `tests/`: Test suite utilizing `pytest`.

## Architecture & Data Flow

1. **Entry Points**: 
   - HTTP requests are handled by FastAPI (e.g., `/health`).
   - Slack events, actions, and commands are ingested and routed to specific handlers in the `features/` directory.
2. **State Management & Database**: 
   - `StateManager` controls transitions for incidents, missions, operations, and workflows, persisting state to SQLite via SQLAlchemy.
3. **Agent Orchestration**:
   - `AgentRegistry` and `SupervisorAgent` use LLM inference to parse incidents, evaluate situations, and dispatch tasks to mini-agents or the `MissionExecutionEngine`.
4. **Background Jobs**:
   - `apscheduler` runs recurring tasks like the `NewsMonitorCoordinator`, `SummaryDigestScheduler`, and `MissionSchedulerBackgroundRunner`.

## Database Models

The SQLite schema natively tracks:
- **Incidents** (includes `parent_id`, `assigned_user_id`, `thread_ts`, `operation_id`, `mission_id`)
- **Operations** (aggregations of incidents/missions)
- **Missions & Workflows** (execution plans and status tracking)
- **Recommendations** (includes assignment and completion tracking)
- **Audit Trails** (logs changes across entities)
- **Watchlists** (severity thresholds, keywords, associated channels)
- **Monitoring Profiles** (custom frequency tracking)

## Environment Variables

CrisisPilot is configured via `.env`. Key variables include:

| Variable | Description |
|---|---|
| `APP_ENV` | Environment mode (default: `development`). |
| `LOG_LEVEL` | Logging verbosity (default: `INFO`). |
| `SLACK_BOT_TOKEN` | Slack Bot User OAuth Token. |
| `SLACK_SIGNING_SECRET` | Slack App Signing Secret. |
| `SLACK_APP_TOKEN` | Slack App-Level Token (for socket mode). |
| `GROQ_API_KEY` | API Key for Groq (LLM provider). |
| `GROQ_MODEL` | The LLM model to use (default: `llama-3.3-70b-versatile`). |
| `DATABASE_URL` | Async database URL (default: `sqlite+aiosqlite:///./storage/crisispilot.db`). |
| `NEWS_API_KEY` | API key for fetching news data.(newsapi.org) |
| `OPENWEATHER_API_KEY` | API key for weather tools. |
| `HITL_WORKFLOW_ENABLED` | Toggle Human-in-the-Loop workflows (default: `True`). |
| `LLM_GUARDRAILS_ENABLED` | Toggle LLM usage guardrails (default: `True`). |

## API Endpoints & Commands

### FastAPI Endpoints
- `GET /health`: Returns the health status of the application and its subsystems.

### Slack Commands & Actions
- `/crisispilot-ping`: Verifies the slash command framework is operational.
- `global_update_status_modal`: Interactive Slack modal triggered by the `global_update_status` action to change states of missions, operations, workflows, and incidents.

## Installation & Setup

1. **Prerequisites**: Python >= 3.11, UV or pip.
2. **Clone and Install**:
   ```bash
   # Using standard pip
   pip install -r requirements.txt
   
   # Or using Hatch/uv (as defined in pyproject.toml)
   pip install -e .
   ```
3. **Environment setup**: 
   Copy `.env.example` to `.env` and fill in the API keys and Slack tokens.
4. **Database Initialization**: 
   The database tables and watchlists are automatically seeded upon application startup.
5. **Run the Application**:
   ```bash
   python -m app.main
   # or
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Development & Testing

Tests are written using `pytest`. The `pytest-asyncio` plugin is heavily used for testing asynchronous database and Slack interactions.

To run tests with coverage reporting:
```bash
pytest --cov=app --cov=core --cov=features --cov=infrastructure --cov=shared --cov-report=term-missing
```

Code quality formatting and linting is handled by `ruff` and `mypy`, which can be run via pre-commit hooks.

## Current Limitations
- Testing coverage and specific configurations for advanced deployments (e.g., Docker/Kubernetes) are not explicitly provided in the core repository context.
- Database locking may occur under heavy concurrent load as it relies on SQLite (multithreading enabled but still constrained by SQLite concurrency).
