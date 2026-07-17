"""Canada-only market defaults for GTM fixtures and MCP data."""

MARKET = {
    "region": "Canada",
    "currency": "CAD",
    "locale": "en-CA",
    "scope": (
        "Canadian partners, customers, market, currency, and outcomes only. "
        "No US persona or USD framing."
    ),
    "compliance_frameworks": ["PHIPA", "PIPEDA", "OSFI", "FINTRAC"],
}
