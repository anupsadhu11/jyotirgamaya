# Jyotirgamaya

A full-stack kundali and panchang app with:
- a polished frontend experience
- a Node/Express web server that serves the frontend and proxies API requests
- a Python backend that computes the astrology reading (live geocoding + sunrise/sunset via Open-Meteo)

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

Configuration lives in `.env` (see `.env.example`):
- `PORT` — Express server port (default `3000`)
- `PYTHON_API_URL` — base URL of the Python service (default `http://127.0.0.1:8000`)
- `DB_PATH` — SQLite file for saved readings (default `jyotirgamaya.db` next to `backend.py`)

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
