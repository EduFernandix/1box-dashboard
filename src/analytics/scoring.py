"""Campaign efficiency scoring.

Computes a composite score (0-100) for each campaign based on
weighted metrics: CPC, CTR, conversion rate, and ROAS.
"""

import pandas as pd


def calculate_campaign_scores(
    campaigns: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Calculate efficiency scores for campaigns.

    Default weights:
        CPC: 0.25 (lower is better)
        CTR: 0.25 (higher is better)
        Conversion Rate: 0.30 (higher is better)
        ROAS: 0.20 (higher is better)

    Args:
        campaigns: DataFrame with campaign metrics.
        weights: Optional custom weight dict.

    Returns:
        DataFrame with added 'efficiency_score' column (0-100).
    """
    # TODO: Implement in Phase 5
    raise NotImplementedError
