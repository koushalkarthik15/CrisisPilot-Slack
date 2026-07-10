# CrisisPilot

CrisisPilot is an autonomous, Slack-native AI operations center designed to continuously monitor external events, manage active operations, execute intelligent missions, and orchestrate incident response directly where teams collaborate.

Built with a domain-driven architectural approach, CrisisPilot transcends traditional incident management by operating as an **Active Operations Platform**—continuously scanning for threats, evaluating situations, and recommending actions before they become full-blown crises.

---

## Key Features

- **Continuous Monitoring & Auto-Provisioning**: Create Monitoring Profiles (e.g., "Hurricane Watch") that automatically provision Operations, Workflows, and Missions.
- **Mission Scheduler Engine**: Autonomous background task execution for data gathering, intelligence analysis, and system reporting.
- **Intelligent Risk Escalation**: Automated Situation Evaluator that tracks observations, computes risk thresholds, and dynamically escalates profiles to critical status.
- **Automated Recommendations**: Uses LLMs to generate actionable Incident Recommendations based on critical monitoring events.
- **Human-in-the-Loop Incident Management**: Slack-integrated dashboards for operators to review recommendations, approve them, and manage incidents to resolution.
- **Immutable Operational Timeline**: A comprehensive audit trail (Timeline Events and Evidence) securely logging every state change, mission outcome, and operator action.

---

## Architecture Overview

CrisisPilot strictly adheres to a feature-first, domain-driven architecture:

1. **Slack UI / Transport**: A FastAPI + Slack Bolt interface translating chat interactions into domain actions.
2. **StateManager / Service Layer**: The central orchestration hub (`StateManager`) coordinates cross-domain workflows between independent services (Monitoring, Missions, Operations, Timeline, Evidence).
3. **Repository / Persistence**: SQLAlchemy 2.0 with aiosqlite, providing deterministic, asynchronous database transactions.
4. **Mini-Agent Framework**: A scalable architecture allowing small, specialized AI agents to execute specific analytical tasks using LLMs (e.g., Groq) and MCP (Model Context Protocol) tools.

---

## Project Structure

```text
SlackAgent/
├── app/               # FastAPI entrypoints, Slack app bootstrap,runtime lifecycle
├── core/              # Global configurations, errors, ServiceRegistry, StateManager
├── features/          # Domain-driven features (Monitoring, Missions, Operations, etc.)
├── infrastructure/    # Database configuration, external API clients, MCP registry
├── shared/            # Shared utilities and helpers
├── docs/              # Comprehensive project documentation (ADRs, Vision, Progress)
├── tests/             # Pytest suite (unit and E2E integration tests)
```

---

## Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI (Async HTTP / Routing)
- **Database**: SQLAlchemy 2.0 + SQLite (In-Memory/File based Async)
- **Integration**: Slack Bolt Framework (Socket Mode)
- **AI / LLM**: Groq Provider (Llama-3 models)
- **Tooling**: `uv` (Dependency management), `pytest` (Testing), `ruff` / `black` (Code Quality)

---

## Configuration Reference

Configuration is managed via `.env`. A sample configuration is provided in `.env.example`.

| Variable | Description |
| -------- | ----------- |
| `SLACK_BOT_TOKEN` | Slack Bot token (`xoxb-`) |
| `SLACK_APP_TOKEN` | Slack App token for Socket Mode (`xapp-`) |
| `GROQ_API_KEY` | API Key for Groq LLM integration |
| `APP_ENV` | Environment (`development`, `production`, `testing`) |
| `LOG_LEVEL` | Application logging level (`INFO`, `DEBUG`) |
| `LLM_GUARDRAILS_ENABLED` | Toggle for LLM request/token usage limits |

---

## Setup & Installation

CrisisPilot relies on `uv` for lightning-fast dependency resolution.

1. **Clone the repository**:
   ```bash
   git clone <repository_url>
   cd SlackAgent
   ```
2. **Install dependencies**:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   uv pip install pytest pytest-asyncio  # For testing
   ```
3. **Environment Setup**:
   ```bash
   cp .env.example .env
   # Edit .env with your specific API keys
   ```

---

## Slack Sandbox Setup & Demo Instructions

To test the application locally within a Slack workspace:

1. Navigate to the [Slack API Apps dashboard](https://api.slack.com/apps).
2. Click **Create New App** -> **From an app manifest**.
3. Copy the contents of `docs/slack_manifest.json` and paste it into the Slack console.
4. Install the App into your Slack Sandbox Workspace.
5. Generate an App-Level Token (with `connections:write` scope) and a Bot Token.
6. Configure these in your `.env` file (`SLACK_APP_TOKEN` and `SLACK_BOT_TOKEN`).

*(Placeholder for Demo Video / Architecture Diagram)*
`![CrisisPilot Demo](placeholder_url)`

---

## Running the Application

Execute the FastAPI server with `uvicorn`:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Running Tests

CrisisPilot includes a comprehensive suite of deterministic unit and integration tests. No external API keys are required to run tests.

```bash
uv run pytest
```

---

## Deployment Overview

CrisisPilot is designed to be easily deployable to cloud-native PAAS environments like Railway or Render. Deployment validation and continuous integration pipelines are configured via GitHub Actions (see `.github/workflows/ci.yml`). Detailed deployment steps will be verified in subsequent release readiness milestones.

---

## Known Limitations

- **In-Memory/SQLite Focus**: Currently designed around SQLite (`aiosqlite`) for ease of deployment and testing. Scaling to distributed environments will require a transition to PostgreSQL.
- **LLM Context Limits**: Mission intelligence features rely on Groq/Llama models which have specific context window limits; extremely large evidence payloads may require text truncation.

---

## Future Enhancements

- **PostgreSQL Migration**: Upgrading the persistence layer to support multi-node scaling.
- **Advanced Predictive Analytics**: Integrating historical incident data for preemptive risk flagging.
- **Multi-Workspace Slack Distribution**: Enabling OAuth 2.0 flows to distribute the app across multiple enterprise Slack organizations simultaneously.
