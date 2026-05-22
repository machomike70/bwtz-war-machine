# Bwtz War Machine — Architecture

**Growth & Utility Engine for Bear Witness $BWTZ**  
*Xtreme Ripple Protocol*

This document describes the current Phase 1 architecture of the Bwtz War Machine and the intended evolution toward coordinated growth tooling across the Xtreme Ripple Protocol ecosystem.

## High-Level System Diagram

```mermaid
flowchart TB
    subgraph "Client / Operator Layer"
        Browser[Browser / Dashboard<br/>http://localhost:8001]
        Human[Human Operator]
    end

    subgraph "API Layer"
        Gateway[Gateway API<br/>:8000<br/>FastAPI proxy + health aggregation]
    end

    subgraph "Core Services (Phase 1)"
        Orchestrator[Agent Orchestrator<br/>:8001<br/>FastAPI<br/>• Serves dark dashboard<br/>• /daily JSON endpoint<br/>• Template generator + DB reader]
        Worker[Worker<br/>Python script + APScheduler<br/>:no public port<br/>• Daily cron jobs (08:00/20:00 UTC)<br/>• Orchestrator client<br/>• Postgres persistence]
    end

    subgraph "Data Layer"
        Postgres[(PostgreSQL 16<br/>daily_posts<br/>accounts<br/>persistence + status)]
    end

    subgraph "Future / Stub Services"
        XBot[X-Twitter-Bot<br/>:8008<br/>stub today → real posting]
        AIServices[AI Microservices<br/>retrieval:8002<br/>memory:8003<br/>tool:8004<br/>guardrail:8005<br/>eval:8006<br/>(currently python -m http.server placeholders)]
    end

    subgraph "Observability"
        Prometheus[Prometheus :9090]
        Grafana[Grafana :3000]
        Redis[(Redis :6379<br/>future queues/cache)]
    end

    Browser -->|GET / + /daily| Orchestrator
    Browser -->|GET /daily| Gateway
    Gateway -->|proxy| Orchestrator
    Human -->|copy + manual post| X[ X / Twitter ]

    Worker -->|GET /daily| Orchestrator
    Worker -->|INSERT / SELECT| Postgres
    Orchestrator -->|SELECT / INSERT fallback| Postgres

    Worker -.->|future POST /orchestrate + queue| XBot
    Orchestrator -.->|future content gen| AIServices
    XBot -.->|future real X API calls| X

    Prometheus -->|scrape| Gateway
    Prometheus -->|scrape| Orchestrator
    Grafana -->|dashboards| Prometheus
```

## Component Responsibilities

### 1. Worker (`apps/worker`)
- Long-running Python process (no uvicorn web server in Phase 1).
- Uses APScheduler with CronTrigger for `DAILY_POST_TIMES`.
- On startup: inits DB schema + account seeds, performs **immediate** generation for "today", then schedules recurring jobs.
- Calls `GET /daily` on orchestrator.
- Persists results to `daily_posts` (idempotent via composite unique key).
- Environment-driven configuration.
- Future: will expose lightweight FastAPI endpoints for manual triggers, status, and will enqueue posting jobs to x-twitter-bot.

### 2. Agent Orchestrator (`apps/agent-orchestrator`)
- Primary user-facing service for Phase 1.
- FastAPI application serving:
  - `GET /` → rich, self-contained dark-mode HTML dashboard with JS copy-to-clipboard + auto-refresh.
  - `GET /daily` → JSON `{ daily_schedule: { "@handle": ["post1", ...] }, source: "database"|"template", ... }`
- DB-preferred: if rows exist for `scheduled_for = today()` in Postgres, returns them (with status metadata).
- Graceful fallback to curated, high-quality static brand-voice templates (`_base_posts_for_account`).
- Future endpoints: `/generate`, `/mark-posted`, `/status`.

### 3. Gateway API (`apps/gateway-api`)
- Thin reverse-proxy / facade.
- Aggregates health (`/health`).
- Proxies `/daily` and future routes to orchestrator (and later x-twitter-bot).
- Single entrypoint for external clients or white-label usage.

### 4. X-Twitter-Bot (`apps/x-twitter-bot`)
- Currently a pricing + stub service.
- Will become the dedicated X posting engine (OAuth 1.0a, media upload, thread support, rate-limit handling, dry-run mode).

### 5. Postgres
- Single source of truth for scheduled and historical posts.
- Tables:
  - `accounts` (seeded handles + brand metadata)
  - `daily_posts` (content, scheduled_for date, status, source, posted_at, notes)
- Simple schema created on first worker start (no Alembic yet).

### 6. Placeholder AI Services
- `retrieval-service`, `memory-service`, `tool-service`, `guardrail-service`, `eval-service`
- Run as `python -m http.server` for now (ports 8002–8006).
- Future: real FastAPI apps with shared-core package, vector DB, guardrails, evaluation harness, xAI/Grok calls.

### 7. Infrastructure
- Redis, Prometheus + Grafana pre-provisioned in compose for later phases.
- All services have healthchecks and `restart: unless-stopped`.

## Request / Data Flows (Phase 1)

1. **Startup / First Use**
   - `docker compose up` brings Postgres → Orchestrator (healthy) → Worker.
   - Worker `init_db()` + immediate `scheduled_job()` → `fetch_or_generate_daily()` → `persist_daily_posts()`.
   - Dashboard at orchestrator port immediately shows posts (source: "database").

2. **Scheduled Run**
   - APScheduler fires → same fetch + persist (duplicate-safe).

3. **Dashboard Interaction**
   - User opens `/` → JS fetches `/daily` → renders cards with copy buttons.
   - 60s polling keeps it fresh.

4. **Manual Regeneration**
   - `docker compose restart worker` triggers fresh `scheduled_job()`.

## Future Evolution (Phase 1 Completion → Phase 2+)

- Worker exposes `/trigger-daily`, `/posts/today`, enqueues to Redis or directly to x-twitter-bot.
- x-twitter-bot implements real posting with per-account credentials, success/failure callbacks, rate limiting.
- Orchestrator adds LLM path: calls retrieval + guardrail + xAI to synthesize fresh posts per brand voice + recent context.
- Shared `packages/shared-core` for common models, clients, logging.
- Full observability, audit logs, approval UI.

## Technology Stack

- Python 3.11 + FastAPI + Uvicorn (web)
- APScheduler (cron)
- psycopg (Postgres async/sync)
- httpx (client calls)
- Docker + Compose (orchestration)
- Mermaid diagrams (this doc)

## Port Reference (local)

| Service              | Port  | Notes                          |
|----------------------|-------|--------------------------------|
| gateway-api          | 8000  | Public proxy                   |
| agent-orchestrator   | 8001  | Dashboard + daily JSON         |
| retrieval-service    | 8002  | Placeholder                    |
| memory-service       | 8003  | Placeholder                    |
| tool-service         | 8004  | Placeholder                    |
| guardrail-service    | 8005  | Placeholder                    |
| eval-service         | 8006  | Placeholder                    |
| x-twitter-bot        | 8008  | Future posting                 |
| postgres             | 5432  | DB                             |
| redis                | 6379  | Future                         |
| prometheus           | 9090  | Metrics                        |
| grafana              | 3000  | Dashboards (admin/admin)       |

This architecture keeps the daily human-in-the-loop tool rock-solid today while providing clean extension points for autonomous growth features.

See [RUNBOOK.md](RUNBOOK.md) for operations and [README.md](../README.md) for getting started.
