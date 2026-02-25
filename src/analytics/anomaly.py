"""Anomaly detection for marketing metrics.

Implements Z-Score (simple) and Isolation Forest (advanced) anomaly
detection for CPC, CTR, conversions, and session metrics.
"""

import pandas as pd


def detect_anomalies_zscore(
    data: pd.Series,
    threshold: float = 2.5,
) -> pd.Series:
    """Detect anomalies using Z-Score method.

    Args:
        data: Time series of metric values.
        threshold: Z-Score threshold (default 2.5 = ~99% confidence).

    Returns:
        Boolean series where True indicates an anomaly.
    """
    # TODO: Implement in Phase 5
    raise NotImplementedError


def detect_anomalies_isolation_forest(
    data: pd.DataFrame,
    contamination: float = 0.05,
) -> pd.Series:
    """Detect anomalies using Isolation Forest (scikit-learn).

    Args:
        data: DataFrame with metric columns.
        contamination: Expected proportion of anomalies.

    Returns:
        Boolean series where True indicates an anomaly.
    """
    # TODO: Implement in Phase 5
    raise NotImplementedError
