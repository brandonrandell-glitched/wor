# GTM Agent Ecosystem

Multi-workflow assistant platform for **Cisco Canada** sellers and partners. Uses **public Cisco content** and **seller-provided inputs** only — no API credentials or logins.

## Market scope

**Canada only** — Canadian partners, customers, compliance frameworks (PHIPA, PIPEDA, OSFI, FINTRAC), **CAD** currency, and Canadian outcomes. Do not apply US partner-growth persona, USD defaults, or US-only vertical framing.

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

## Narrative model — security-led, platform-capable

Inbound traffic is expected **security-first**, but networking, data centre, and collaboration are **first-class entry points** when that is how the deal arrives. The content engine routes narrative depth — never catalogue-sells across pillars.

| When | Story mode | Behaviour |
|------|------------|-----------|
| CISO-only sponsor, security line-item budget, Qualified on named security motion | `security-only` | SME depth on security only — no pull-through |
| Default security inbound; customer names refresh, sprawl, hybrid, AI | `security-led` | Security door → platform thread when earned |
| Network / DC / collab RFP or renewal first | `pillar-first` + pillar | Answer as SME on that pillar; optional pivot when policy/compliance/identity surfaces |
| Security opened the door; single-pillar evaluation | `pillar-deep` + pillar | Tie-back to security trigger, then SME depth |

| Tool | Use |
|------|-----|
| `cisco-content` → `build_platform_brief` | Drafting context for any story mode above |
| `cisco-content` → `get_platform_story` | Rehearse routing, pivot lines, entry thread before calls |
| `proposal-tools` → `recommend_platform_story` | Map pain points to products; pass `entry_pillar` for non-security inbound |
| `partner-ops` → `platform_view` | See security entry vs pull-through in pipeline |

**Story modes:** `security-led` (default) · `security-only` · `pillar-first` + pillar · `pillar-deep` + pillar

**Entry pillars:** `security` · `networking` · `data-center` · `collaboration`

## Customer lifecycle (colleague content matrix)

CX spine: **ANALYZE → PLACE → LAND → ADOPT → EXPAND → RENEW** (with ANALYZE/PLACE foundations).

| Lifecycle | Partner goal | Deal stage | Primary tools |
|-----------|--------------|------------|---------------|
| analyze | Strategic Consultant | 10 Early, 25 Qualified | `sni-scorer`, `extract_pain_points`, `get_content_matrix` |
| place | Trusted Advisor | 25 Qualified | `build_platform_brief`, `get_platform_story` |
| land | Thought Leader | 50 Evaluation | `recommend_platform_story`, proposal workflow |
| adopt | Reliable Operator | 75 Negotiation | discovery brief, `score_assessment` |
| expand | Strategic Services Partner | post-close | `platform_view`, `recommend_platform_story` |
| renew | Trusted Partner | 90 Close | `commerce.get_renewal_context`, `suggest_license_bundle` |

| Tool | Use |
|------|-----|
| `cisco-content` → `get_content_matrix` | Assets, actions, certs, MEDDPICC focus per stage |
| `cisco-content` → `get_lifecycle_guide` | Full spine + 9-step journey |
| `partner-ops` → `lifecycle_view` | Pipeline by lifecycle stage |
| `proposal-tools` → `meddpicc_gaps` | Qualification gaps + questions by stage |
| `commerce` → `get_renewal_context` | Renewal fixture (Acme demo) |

Discovery and proposal workflows capture optional **MEDDPICC** before confirm.

## Tests

```bash
.venv/bin/python -m pytest tests/ -v
```
