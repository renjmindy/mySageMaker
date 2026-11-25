# Jtron Maintenance RAG — Backend

FastAPI backend on the Linux host. Stores users, conversation sessions, messages,
and citations in Postgres. Proxies prompts to the DGX Spark RAG service over a
long-lived WebSocket and streams tokens back to the browser via SSE.

## Run locally with Docker Compose

```bash
cp .env.example .env
# edit .env — set SECRET_KEY and DGX_RAG_WS_URL
docker compose up --build
```

The API is then at `http://<linux-host>:8080`.

## Run without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env     # edit values
alembic upgrade head
uvicorn app.main:app --reload --port 8080
```

## Smoke test

```bash
curl -s http://localhost:8080/healthz

curl -s -c cookies.txt -X POST http://localhost:8080/auth/register \
  -H 'content-type: application/json' \
  -d '{"email":"me@example.com","password":"correct-horse-battery","display_name":"Me"}'

SESSION_ID=$(curl -s -b cookies.txt -X POST http://localhost:8080/sessions \
  -H 'content-type: application/json' -d '{}' | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

curl -N -b cookies.txt -X POST "http://localhost:8080/sessions/$SESSION_ID/messages" \
  -H 'content-type: application/json' \
  -d '{"content":"How do I open the system controller cabinet?"}'
```

## DGX RAG WebSocket contract (assumed)

Replace `app/rag_client.py` protocol handling once the real contract is known.
Current assumption, sent on one shared WS multiplexed by `request_id`:

- Client → DGX: `{"type":"query","request_id":"...","prompt":"...","history":[...]}`
- DGX → Client: one or more frames with the same `request_id`:
  - `{"type":"token","text":"..."}`
  - `{"type":"citation","source":"...","page":N,"snippet":"...","score":0.8}`
  - `{"type":"error","message":"..."}`
  - `{"type":"done"}`

## Layout

```
app/
  main.py           FastAPI entry, lifespan, CORS, routers
  config.py         env settings
  db.py             SQLAlchemy engine + session
  models.py         users / sessions / messages / citations
  schemas.py        Pydantic request/response
  deps.py           current_user cookie dep
  auth/             register, login, logout, me, cookie signing
  sessions/         CRUD routes
  messages/         SSE streaming endpoint + list
  rag_client.py     long-lived multiplexed WS client to DGX
alembic/            migrations
```
