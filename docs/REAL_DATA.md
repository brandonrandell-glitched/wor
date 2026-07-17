# Real data (production use)

Move from the **Acme demo** to your own accounts, partner book, and renewal data — still **no API credentials**. You edit local JSON files (gitignored) or mount them on Render.

## Quick start

```bash
# 1. Create editable real-data files from templates
python scripts/init_real_data.py

# 2. Edit your accounts (CAD amounts, real names)
#    fixtures/real_customers.json
#    fixtures/real_partner_ops.json      (optional)
#    fixtures/real_commerce_renewals.json (optional)

# 3. Use real data (auto switches when files exist)
export GTM_DATA_MODE=real   # or leave auto

# 4. Restart web app / redeploy Render
python -m web.app
```

## Data modes

| `GTM_DATA_MODE` | Behaviour |
|-----------------|-----------|
| `auto` (default) | Use `fixtures/real_*.json` when present; else demo Acme |
| `real` | Prefer real files; fall back to demo only if missing |
| `demo` | Always demo/sample data |

## Customer accounts (`fixtures/real_customers.json`)

Multi-account schema:

```json
{
  "_schema": "gtm-customers-v1",
  "_currency": "CAD",
  "customers": {
    "Your Customer Name": {
      "customer_account": "Your Customer Name",
      "industry": "Financial Services",
      "org_size": "500-1000",
      "deal_id": "OPP-2026-00001",
      "cisco_technologies_proposed": ["Cisco Secure Access"],
      "current_infrastructure": "...",
      "opportunities": [
        {"deal_id": "OPP-2026-00001", "name": "Motion name", "stage": "Qualified", "amount": 185000}
      ]
    }
  }
}
```

**Import from a JSON export:**

```bash
python scripts/import_customers.py path/to/account_export.json
```

Fields map from Salesforce-style exports (`Account Name`, `Organization Size`, etc.).

`savm_id` is loaded if present but **never** appears in seller-facing output.

## Partner book (`fixtures/real_partner_ops.json`)

Copy template from `fixtures/templates/partner_ops.template.json`.

- MCP `partner-ops` reads this file in `auto`/`real` mode.
- **Writes** (upsert partner/deal) go to `real_partner_ops.json`, not the public sample.

## Commerce / renewals (`fixtures/real_commerce_renewals.json`)

Copy template from `fixtures/templates/commerce_renewals.template.json`.

Used by `commerce` MCP: `get_renewal_context`, `list_renewals_due`.

## Render (live deployment)

Ephemeral disk resets on deploy. For persistent real data:

1. Render dashboard → **Disks** → add disk (e.g. 1 GB) mounted at `/var/data/fixtures`
2. Set env var: `GTM_FIXTURES_DIR=/var/data/fixtures`
3. Shell into instance once: `python scripts/init_real_data.py`
4. Upload/edit JSON via Render shell or SFTP

Or keep real files in a **private repo** branch and bake into Docker (not recommended for PII).

## Web UI

- `GET /api/customers` — lists accounts from real or demo store
- `GET /api/health` — shows `data.effective` (`real` vs `demo`)

Customer name field suggests accounts from your real file when loaded.

## What stays public

| Source | Stays fixture-based |
|--------|---------------------|
| Product summaries, proof points, competitive | `fixtures/public_content.json` (public Cisco content) |
| Pain-point → product matching patterns | `fixtures/proposal_tools_data.json` |
| Cisco content matrix / lifecycle MCP | `mcp-framework/servers/data/` |

## Security

- `fixtures/real_*.json` is **gitignored** — do not commit customer PII.
- Render: use private services or auth gateway if exposing real account names externally.
