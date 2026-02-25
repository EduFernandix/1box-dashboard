"""Formatting helpers for the dashboard."""


def format_eur(value: float) -> str:
    """Format as EUR currency."""
    if abs(value) >= 1_000_000:
        return f"\u20ac{value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"\u20ac{value:,.0f}"
    return f"\u20ac{value:,.2f}"


def format_micros(micros: int) -> float:
    """Convert micros to EUR."""
    return micros / 1_000_000


def format_pct(value: float) -> str:
    """Format as percentage."""
    return f"{value:.1f}%"


def format_number(value: int | float) -> str:
    """Format with thousand separators."""
    if isinstance(value, float):
        return f"{value:,.1f}"
    return f"{value:,}"


def channel_label(source: str, medium: str) -> str:
    """Create a human-readable channel label."""
    key = (source.lower(), medium.lower())
    labels = {
        ("google", "cpc"): "Google Ads",
        ("google", "organic"): "Organic Search",
        ("(direct)", "(none)"): "Direct",
        ("bing", "cpc"): "Bing Ads",
    }
    if key in labels:
        return labels[key]
    if medium.lower() == "referral":
        return f"Referral ({source})"
    if medium.lower() == "organic":
        return "Organic Search"
    if medium.lower() in ("cpc", "ppc"):
        return f"Paid ({source})"
    return f"{source} / {medium}"
