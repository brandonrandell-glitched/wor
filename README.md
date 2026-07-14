# GTM Agent Ecosystem

Multi-workflow assistant platform for Cisco sellers: **proposals**, **discovery prep**, and **competitive briefs**. Uses **public Cisco content** and **seller-provided inputs** only — no API credentials or logins.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Web UI (workflow picker)
python -m web.app
# Open http://127.0.0.1:8080

# CLI
python -m agents.cli "Acme Financial Services" --workflow proposal --generate
python -m agents.cli "Acme Financial Services" --workflow discovery --generate
python -m agents.cli "Acme Financial Services" --workflow competitive --generate
```

## Workflows

| Workflow | What it does | Document output |
|----------|--------------|-----------------|
| Build Proposal | Full Q&A intake → review → JSON | `.docx` or `.pptx` |
| Discovery Prep | Account context, pains, technologies, questions | `.docx` brief |
| Competitive Brief | Technologies + competitor selection → positioning | `.docx` brief |

See [AGENTS.md](AGENTS.md) for architecture, handoffs, and MCP tool details.

## Data Sources

| Source | What it provides |
|--------|------------------|
| `fixtures/public_content.json` | Public product summaries, proof points, competitive, offers |
| `fixtures/salesforce_customer.json` | Optional demo scenario (`Acme Financial Services`) |
| `fixtures/proposal_tools_data.json` | Pain-point and product-matching patterns |
| Seller Q&A | Real customer details you enter during intake |

No SalesConnect, Salesforce, or OAuth tokens required.

## Architecture

```
agents/router.py                 ← routes to proposal / discovery / competitive
lib/gtm_tools.py                 ← shared tool layer
lib/public_content.py            ← public Cisco content
story_library/                   ← per-workflow document generators
web/app.py                       ← web UI
mcp_servers/                     ← Cursor MCP integration
```

## Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

See [docs/CREDENTIALS.md](docs/CREDENTIALS.md) for details on the no-credentials approach.
