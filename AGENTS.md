# GTM Agent Ecosystem

Multi-workflow assistant platform for Cisco sellers. Uses **public Cisco content** and **seller-provided inputs** only — no API credentials or logins.

## Workflows

| Workflow | Agent | Output |
|----------|-------|--------|
| **Build Proposal** | `ProposalAssistant` | Word/PPT proposal with proof points, competitive positioning, commercial offer |
| **Discovery Prep** | `DiscoveryAssistant` | Discovery brief (`.docx`) with pain points, technologies, and meeting questions |
| **Competitive Brief** | `CompetitiveAssistant` | Competitive brief (`.docx`) positioning Cisco vs selected competitors |

## Architecture

```
agents/router.py              ← workflow picker
agents/proposal_assistant.py  ← full proposal intake
agents/discovery_assistant.py ← discovery prep intake
agents/competitive_assistant.py ← competitive brief intake
lib/gtm_tools.py              ← shared tools (Salesforce fixtures, pain points, products)
lib/public_content.py         ← public Cisco proof points, products, competitive, offers
story_library/                ← document generators per workflow
mcp_servers/                  ← Cursor MCP tools (stdio)
web/app.py                    ← web UI with workflow picker
```

## Handoffs

Workflows share `lib/gtm_tools.py` and can hand off context via confirmed JSON:

- **Discovery → Proposal**: Use discovery JSON pain points and technologies as seller inputs when starting a proposal.
- **Competitive → Proposal**: Pass `Competitors` into proposal JSON to customize competitive positioning section.
- **Proposal → Competitive**: Use confirmed technologies from proposal JSON when building a competitive brief.

## Running

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Web UI (workflow picker)
python -m web.app

# CLI
python -m agents.cli "Acme Financial Services" --workflow discovery --generate
python -m agents.cli "Acme Financial Services" --workflow competitive --generate
python -m agents.cli "Acme Financial Services" --workflow proposal --generate
```

## Data Sources

| Source | Purpose |
|--------|---------|
| `fixtures/public_content.json` | Public products, proof points, competitive, offers |
| `fixtures/salesforce_customer.json` | Demo scenario for `Acme Financial Services` |
| `fixtures/proposal_tools_data.json` | Pain-point and product-matching patterns |
| Seller Q&A | Customer-specific details during intake |

## MCP Tools (Cursor)

Configured in `.cursor/mcp.json`:

- **salesforce** — `get_customer_context`, `suggest_opportunities`
- **proposal-tools** — `extract_pain_points`, `recommend_products`
- **salesconnect** — `get_proof_point`, `search_competitive`, `get_offer_detail`

All tools use fixtures and public content only.

## Tests

```bash
.venv/bin/python -m pytest tests/ -v
```
