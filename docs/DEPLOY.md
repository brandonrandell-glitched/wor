# Deploy GTM Agent Ecosystem (live web UI)

The web UI is a Flask app (`web/app.py`) served with **gunicorn** in production.

## Option A — Render (recommended, free tier)

1. Push this repo to GitHub (already on `main`).
2. Open [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect `brandonrandell-glitched/wor` (or your fork).
4. Render reads `render.yaml` and creates the **gtm-agent-ecosystem** web service.
5. When deploy finishes, open the `*.onrender.com` URL.

Health check: `GET /api/health`

## Option B — Docker (any host)

```bash
docker build -t gtm-agent-ecosystem .
docker run --rm -p 8080:8080 gtm-agent-ecosystem
```

Open http://localhost:8080

## Option C — Local production mode

```bash
source .venv/bin/activate
pip install -r requirements.txt
HOST=0.0.0.0 PORT=8080 FLASK_DEBUG=0 gunicorn --bind 0.0.0.0:8080 --workers 1 web.app:app
```

## Notes

- **Single worker required** — workflow sessions live in memory; do not scale gunicorn workers above 1 without external session storage.
- **No credentials** — public fixtures only; safe for demo and partner enablement.
- Generated documents are written to `output/` on the instance (ephemeral on free Render).
