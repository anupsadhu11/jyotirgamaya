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

You need both services running.

1. Start the Python astrology service:
   ```
   python backend.py
   ```
2. In another terminal, install Node dependencies and start the web server:
   ```
   npm install
   npm start
   ```
   (requires Node.js 18+, for built-in `fetch`)
3. Open http://localhost:3000/

Configuration lives in `.env` (see `.env.example`):
- `PORT` — Express server port (default `3000`)
- `PYTHON_API_URL` — base URL of the Python service (default `http://127.0.0.1:8000`)

## API

- GET /api/health
- POST /api/astrology/reading — proxied to the Python service
