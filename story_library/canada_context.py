"""Canada-specific document context for generated briefs and proposals."""

from __future__ import annotations

from lib.market import MARKET

FINANCIAL_INDUSTRIES = {
    "Financial Services",
    "Banking",
    "Insurance",
    "Credit Union",
}


def compliance_note(industry: str = "") -> str:
    ind = (industry or "").strip()
    if ind in FINANCIAL_INDUSTRIES or "financial" in ind.lower():
        frameworks = ", ".join(MARKET["compliance_frameworks"])
        return f"Canadian compliance context: {frameworks}."
    return "Canadian market context applies (partners, customers, and outcomes)."


def market_context_section(industry: str = "") -> tuple[str, str]:
    body = (
        f"Region: {MARKET['region']}\n"
        f"Currency: {MARKET['currency']}\n"
        f"Locale: {MARKET['locale']}\n"
        f"{compliance_note(industry)}"
    )
    return ("Market Context (Canada)", body)


def prepend_market_sections(
    sections: list[tuple[str, str]],
    industry: str = "",
) -> list[tuple[str, str]]:
    return [market_context_section(industry)] + sections
