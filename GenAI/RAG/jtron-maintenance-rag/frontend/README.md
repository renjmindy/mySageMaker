# Jtron Maintenance RAG — Frontend

Vite + React + TypeScript + Tailwind. Streams assistant replies over SSE and
renders citation chips linked to a source panel.

## Dev (against a running backend)

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
# Vite proxies /auth /sessions /healthz to http://localhost:8080 by default.
# Point elsewhere with: VITE_BACKEND_URL=http://192.168.3.56:8080 npm run dev
```

## Production (via docker compose)

The root `docker-compose.yml` builds `frontend/` as an nginx image that
serves the SPA on the host port and reverse-proxies `/auth`, `/sessions`,
`/healthz` to the backend container internally. From the user's browser
there is only one origin, so no CORS config is needed.

```bash
cd backend                  # compose file lives there
docker compose up -d --build
# visit http://<linux-host>:8080
```

## Structure

```
src/
  main.tsx            entry + <BrowserRouter>
  App.tsx             route guard (/login vs /app) based on useAuth
  index.css           Tailwind directives
  api.ts              fetch helpers + SSE via @microsoft/fetch-event-source
  types.ts            User, ChatSession, Message, Citation
  hooks/useAuth.ts    loads /auth/me on mount, exposes login/register/logout
  routes/
    Login.tsx         email + password form with register toggle
    Chat.tsx          sessions sidebar + message list + composer + citations panel
  components/
    SessionList.tsx   left sidebar
    MessageList.tsx   scrollable messages with streaming bubble + citation chips
    Composer.tsx      Enter to send, Shift+Enter newline
    CitationsPanel.tsx right-side source preview
```
