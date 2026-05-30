# Intervals.icu MCP HTTP Wrapper

A **FastAPI + MCP** server that exposes Intervals.icu tools to MCP-compatible assistants through a remote URL, with HTTP debug endpoints, endurance-focused analytical tools, optional API-key protection for `/mcp`, and full calendar event management.

This project relies on the Intervals.icu Open API, which provides access to activities, wellness data, planned workouts, calendar events, and other athlete resources through API key or OAuth 2.0 authentication. Automatic exposure of FastAPI endpoints as MCP tools is handled through `fastapi_mcp`, which mounts an MCP HTTP server on a path such as `/mcp`. [intervals](https://www.intervals.icu/features/open-api/)

## Features

- Exposes FastAPI endpoints as **MCP tools** through `FastApiMCP`. [raw.githubusercontent](https://raw.githubusercontent.com/tadata-org/fastapi_mcp/main/README.md)
- Provides directly usable HTTP routes for debugging and local testing.
- Centralizes access to Intervals.icu with more structured responses than raw API JSON.
- Adds endurance-focused analytical tools such as histograms, best efforts, intervals, activity streams, and weekly running volume.
- Supports **full calendar event management**: create, update, delete, bulk operations, and duplication.
- Supports **rich activity search** returning complete performance metrics (power, HR, training load, intensity).
- Supports remote MCP access protection with an HTTP API key.

## Use cases

This wrapper is well suited for Perplexity, Claude Desktop, Cursor, Cline, or any client able to consume a remote MCP server URL. The FastAPI-MCP pattern mounts the MCP server directly on the FastAPI application, typically at `/mcp`. [medium](https://medium.com/@miki_45906/how-to-build-mcp-server-in-python-using-fastapi-d3efbcb3da3a)

Typical use cases include:

- Querying recent activities and structured summaries.
- Retrieving wellness data and training load / form metrics.
- Exploring intervals, streams, and best efforts for a given activity.
- Aggregating running volume by week.
- Searching activities with full performance details (power, heart rate, TSS, intensity).
- Planning and managing training calendar events (WORKOUT, NOTE, RACE, GOAL).
- Giving an AI assistant controlled access to a personal Intervals.icu account.

## Architecture

The project is built around a standard FastAPI application enhanced with `FastApiMCP`, which turns selected endpoints into remotely available MCP tools. The MCP server is then mounted on `/mcp`, which matches the documented FastAPI-MCP integration model. [raw.githubusercontent](https://raw.githubusercontent.com/tadata-org/fastapi_mcp/main/README.md)

Typical layout:

```text
app/
├── wrapper_server.py
├── core/
│   ├── client.py
│   └── utils.py
└── routes/
    ├── activities.py
    ├── athlete.py
    ├── events.py
    ├── plans.py
    └── wellness.py
```

### Logical organization

- `core/client.py`: HTTP calls to the Intervals.icu API (`GET`, `POST`, `PUT`, `DELETE`).
- `core/utils.py`: parsing, filtering, and analysis helpers.
- `routes/activities.py`: activities, details, local search, full search with performance metrics.
- `routes/athlete.py`: athlete profile and fitness summary.
- `routes/events.py`: calendar event management (create, update, delete, bulk, duplicate).
- `routes/plans.py`: planned workouts and filters.
- `routes/wellness.py`: daily and range wellness endpoints.
- `wrapper_server.py`: FastAPI assembly, security, and MCP exposure.

## Exposed tools

The MCP instance exposes the following operations referenced in `FastApiMCP(include_operations=...)`:

| Domain | Tools |
|---|---|
| Athlete | `get_athlete_profile`, `get_fitness_summary` |
| Activities | `get_activities`, `get_activity_details`, `search_activities_local`, `search_activities_full` |
| Wellness | `get_wellness`, `get_wellness_for_date` |
| Plans | `get_plan_workouts_filtered` |
| Analysis | `get_activity_streams`, `get_activity_intervals`, `get_best_efforts`, `get_best_efforts_debug`, `get_power_histogram`, `get_hr_histogram`, `get_pace_histogram`, `get_running_volume_by_week` |
| Calendar | `get_events`, `create_event`, `update_event`, `delete_event`, `bulk_create_events`, `bulk_delete_events`, `duplicate_event` |

### search_activities_full vs search_activities_local

| | `search_activities_local` | `search_activities_full` |
|---|---|---|
| Recherche | Filtre local sur activités récentes | Recherche native Intervals.icu |
| Données retournées | Résumé minimal (id, name, date, type, distance) | Détails complets (power, HR, TSS, HRSS, TRIMP, intensity, cadence) |
| Usage recommandé | Recherche rapide par nom | Analyse de performance sur une activité ciblée |

### Événements calendrier

Les événements supportent quatre catégories : `WORKOUT`, `NOTE`, `RACE`, `GOAL`. Les champs `type`, `moving_time`, `distance` et `icu_training_load` s'appliquent principalement aux événements `WORKOUT`.

## Requirements

- Python 3.11+ recommended.
- An Intervals.icu account with a personal API key, since the API supports personal access by API key. [intervals](https://www.intervals.icu/features/open-api/)
- An Intervals.icu athlete ID.
- An MCP client or HTTPS reverse proxy for remote exposure.

## Environment variables

Minimal example:

```env
INTERVALS_API_KEY=your_intervals_api_key
INTERVALS_ATHLETE_ID=your_athlete_id
MCP_API_KEY=your_remote_mcp_api_key
```

### Main variables

| Variable | Purpose |
|---|---|
| `INTERVALS_API_KEY` | Intervals.icu API key used by the wrapper to call the upstream API. |
| `INTERVALS_ATHLETE_ID` | Target athlete identifier on Intervals.icu. |
| `MCP_API_KEY` | API key expected by the server to authorize access to the remote MCP endpoint. |

## Installation

```bash
git clone <your-repo-url>
cd <your-repo>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Local run

Example with Uvicorn:

```bash
uvicorn wrapper_server:app --host 0.0.0.0 --port 8000
```

If your entry point lives under `app/`, adapt the command accordingly, for example:

```bash
uvicorn app.wrapper_server:app --host 0.0.0.0 --port 8000
```

Once started, the MCP server is typically available at:

```text
http://localhost:8000/mcp
```

Mounting an MCP server on `/mcp` matches the standard `fastapi_mcp` behavior described in its documentation. [medium](https://medium.com/@miki_45906/how-to-build-mcp-server-in-python-using-fastapi-d3efbcb3da3a)

## Securing remote access

The project can protect `/mcp` using an HTTP API key enforced by the FastAPI application. The approach is to require a header such as `X-API-Key` or a bearer token before authorizing incoming requests to the MCP endpoint.

Typical flow:

- The server reads `MCP_API_KEY` from the environment.
- The remote MCP client sends an API key in an HTTP header.
- Any request without a valid key receives `401 Unauthorized`.

This is especially useful when a remote Perplexity connector is configured against a public URL such as `https://your-domain.example.com/mcp`.

## Docker Compose example

```yaml
services:
  intervals-icu-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      INTERVALS_API_KEY: "${INTERVALS_API_KEY}"
      INTERVALS_ATHLETE_ID: "${INTERVALS_ATHLETE_ID}"
      MCP_API_KEY: "${MCP_API_KEY}"
```

Docker Compose variable interpolation uses `${VAR}` syntax rather than `{VAR}`. [docs.docker](https://docs.docker.com/reference/compose-file/interpolation/)

## HTTP test examples

### Healthcheck

```bash
curl http://localhost:8000/health
```

### MCP initialize without authentication

```bash
curl -i -X POST "http://localhost:8000/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {
        "name": "curl",
        "version": "1.0"
      }
    }
  }'
```

### MCP initialize with API key

```bash
curl -i -X POST "https://your-domain.example.com/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-API-Key: ${MCP_API_KEY}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {
        "name": "curl",
        "version": "1.0"
      }
    }
  }'
```

If authentication is configured correctly, the response should be `200 OK` with a valid JSON-RPC `initialize` payload.

### Créer un événement calendrier

```bash
curl -X POST "http://localhost:8000/events" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date_local": "2026-06-10",
    "name": "Sortie longue Z2",
    "category": "WORKOUT",
    "type": "Run",
    "moving_time": 5400,
    "distance": 15000,
    "icu_training_load": 80
  }'
```

### Recherche d'activités avec détails complets

```bash
curl "http://localhost:8000/activities/search/full?query=sortie+longue&limit=5"
```

## Perplexity integration

Perplexity supports adding remote MCP connectors with connector-side authentication configuration. For this project, the target setup is typically: [perplexity](https://www.perplexity.ai/help-center/en/articles/13915507-adding-custom-remote-connectors)

- Server URL: `https://your-domain.example.com/mcp`
- Auth type: API Key
- Header expected by the server: `X-API-Key` or, depending on the chosen strategy, `Authorization: Bearer <key>`
- Value: the same key as `MCP_API_KEY`

A robust server-side strategy is to accept both `X-API-Key` and `Authorization: Bearer`, which helps maintain compatibility across different MCP clients and connector implementations.

## Useful HTTP endpoints

Besides `/mcp`, the project generally exposes:

- `/`: root information
- `/health`: healthcheck
- `/activities`
- `/activities/details`
- `/activities/search`
- `/activities/search/full`
- `/events` — `GET`, `POST`
- `/events/{id}` — `PUT`, `DELETE`
- `/events/bulk` — `POST`, `DELETE`
- `/events/{id}/duplicate` — `POST`
- `/athlete/profile`
- `/athlete/fitness`
- `/wellness`
- `/plan-workouts/filtered`
- `/activity-streams`
- `/activity-intervals`
- `/best-efforts`
- `/power-histogram`
- `/hr-histogram`
- `/pace-histogram`
- `/running-volume-by-week`

## Differences from eddmann's project

eddmann's project provides a rich Intervals.icu MCP server with a strongly MCP-native design. This implementation follows a different approach: [lobehub](https://lobehub.com/mcp/eddmann-intervals-icu-mcp?activeTab=score)

- it uses **FastAPI** to keep endpoints directly testable over HTTP;
- it uses **FastApiMCP** to expose these endpoints as MCP tools;
- it favors structured responses tailored to personal running and cycling workflows;
- it exposes write operations (create, update, delete events) directly as MCP tools;
- it makes operational debugging easier through explicit HTTP routes.

## Troubleshooting

### `/mcp` returns 500

Common cause: `MCP_API_KEY` is missing from the container environment. Check with:

```bash
docker exec -it <container_name> printenv MCP_API_KEY
```

### `/mcp` returns 401

Common causes:

- mismatch between client and server key;
- incorrect Docker environment variable injection;
- value injected literally as `{MCP_API_KEY}` instead of `${MCP_API_KEY}` or the actual secret. [docs.docker](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)

### Authentication works with curl but not with Perplexity

Probable cause: the remote connector sends authentication in a different format. In that case, it is recommended to accept both `X-API-Key` and `Authorization: Bearer` in the middleware.

## Possible roadmap

- Add more Intervals.icu analytical tools.
- Enrich `athlete` and `wellness` responses further.
- Add automated tests for critical endpoints.
- Generate more detailed OpenAPI / MCP documentation.
- Add finer-grained authentication by path or role.

## References

- FastAPI-MCP: automatic exposure of FastAPI endpoints as MCP tools. [raw.githubusercontent](https://raw.githubusercontent.com/tadata-org/fastapi_mcp/main/README.md)
- Perplexity remote MCP connector documentation. [perplexity](https://www.perplexity.ai/help-center/en/articles/13915507-adding-custom-remote-connectors)
- Intervals.icu Open API with API key and OAuth 2.0 support. [intervals](https://www.intervals.icu/features/open-api/)
