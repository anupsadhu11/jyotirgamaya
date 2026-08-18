# Jyotirgamaya

A full-stack kundali and panchang app with:
- a polished frontend experience
- a Node/Express web server that serves the frontend and proxies API requests
- a Python backend that computes the astrology reading (live geocoding + sunrise/sunset via Open-Meteo)
- **Ask Guruji** — an in-character Vedic astrology chat persona (Google Gemini API) that answers grounded in your own generated chart

## Architecture

The frontend talks only to the Node/Express server, which proxies
`/api/astrology/reading` to the Python service. This keeps a single source
of truth for the astrology calculations (Python) instead of duplicating the
logic in both servers.

```
browser -> Express (server.js, :3000) -> Python (backend.py, :8000)
```

## Run locally

You need both services running, in two separate terminals.

1. Python astrology service (first time only: create a venv and install deps):
   ```
   python -m venv .venv
   .venv\Scripts\activate      # Windows; use `source .venv/bin/activate` on macOS/Linux
   pip install -r requirements.txt
   python backend.py
   ```
2. In another terminal, Node web server:
   ```
   npm install
   npm start
   ```
   (requires Node.js 18+, for built-in `fetch`)
3. Open http://localhost:3000/ (the dashboard is at http://localhost:3000/dashboard.html)

Configuration lives in `.env` (see `.env.example`), read by both the Node
server and the Python service (via `python-dotenv`):
- `PORT` — Express server port (default `3000`). Node-only; the Python side
  intentionally uses differently-named vars below so the two don't collide
  now that both read the same `.env` file.
- `PYTHON_API_URL` — base URL of the Python service, used by Express to proxy to it (default `http://127.0.0.1:8000`)
- `PYTHON_PORT` / `PYTHON_HOST` — what the Python service itself binds to (defaults `8000` / `127.0.0.1`)
- `DB_PATH` — SQLite file for saved readings (default `jyotirgamaya.db` next to `backend.py`)
- `GEMINI_API_KEY` — required for the "Ask Guruji" tab; get one at
  https://aistudio.google.com/apikey. Without it, Guruji responds
  with a clear "not configured" message instead of failing silently.
- `GURUJI_MODEL` — optional, overrides the model Guruji uses (default `gemini-2.5-flash`)

## Tests

```
python -m unittest discover -s tests -t . -v
```

## API

- GET /api/health
- POST /api/astrology/reading — generate a reading (not saved)
- POST /api/readings — generate and save a reading
- GET /api/readings — list saved readings
- GET /api/readings/:id — fetch one saved reading
- DELETE /api/readings/:id — delete a saved reading
- POST /api/guruji/chat — ask Guruji a question (`{message, history, reading}` → `{reply}`)
