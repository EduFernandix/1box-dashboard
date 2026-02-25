"""Time series forecasting for marketing metrics.

Uses statsmodels for ARIMA-based forecasting of cost, conversions,
and traffic with confidence intervals.
"""

import pandas as pd


def forecast_metric(
    data: pd.Series,
    periods: int = 14,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Forecast a metric N periods into the future.

    Args:
        data: Historical time series (daily frequency).
        periods: Number of days to forecast (7, 14, or 30).
        confidence: Confidence interval width.

    Returns:
        DataFrame with columns: date, forecast, lower_bound, upper_bound.
    """
    # TODO: Implement in Phase 5 (ARIMA or Prophet)
    raise NotImplementedError
