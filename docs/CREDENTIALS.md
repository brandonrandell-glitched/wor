# Credentials

**No API credentials or tokens are required.**

This project uses:

1. **Public Cisco content** — product summaries and citeable proof points from `fixtures/public_content.json` (sourced from public Cisco portfolio pages and publications)
2. **Seller inputs** — everything you provide during the guided Q&A (customer name, pain points, technologies, etc.)
3. **Demo scenarios** — optional sample customer data in `fixtures/salesforce_customer.json` for testing with `Acme Financial Services`

## What we do not use

- SalesConnect login or API tokens
- Salesforce API tokens
- Cisco OAuth / API Console credentials

## Adding more public content

Edit `fixtures/public_content.json` to add:

- `proof_points` — publicly citeable stats with `classification: "Public"`
- `product_summaries` — descriptions aligned with public cisco.com product pages

Only **Public** classified proof points are included in proposals (cite-or-null rule).
