# GTM Agent Ecosystem

Proposal-building assistant for Cisco sellers. Uses **public Cisco content** and **seller-provided inputs** only — no API credentials or logins.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Web UI
python -m web.app
# Open http://127.0.0.1:8080

# CLI
python -m agents.cli "Acme Financial Services" --generate
```

## Data Sources

| Source | What it provides |
|--------|------------------|
| `fixtures/public_content.json` | Public product summaries and citeable proof points |
| `fixtures/salesforce_customer.json` | Optional demo scenario (`Acme Financial Services`) |
| `fixtures/proposal_tools_data.json` | Pain-point and product-matching patterns |
| Seller Q&A | Real customer details you enter during intake |

No SalesConnect, Salesforce, or OAuth tokens required.

## Architecture

```
agents/proposal_assistant.py   ← conversation state machine
web/app.py                     ← web UI
story_library/generator.py     ← proposal document generation
lib/public_content.py          ← public Cisco content only
fixtures/                      ← public content + demo scenarios
```

## Output

After intake confirmation, generate real deliverables:

- **Word** → `.docx` with executive summary, challenges, solution, proof points, competitive positioning
- **PPT** → `.pptx` slide deck

Section headers are localized to the language selected during intake (EN, DE, FR, ES, IT, JA, zh-CN).

## Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

See [docs/CREDENTIALS.md](docs/CREDENTIALS.md) for details on the no-credentials approach.
