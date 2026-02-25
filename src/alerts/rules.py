"""Alert rule loader and validator.

Parses config/alerts.yaml into AlertRuleConfig Pydantic models
and validates rule definitions.
"""

from pathlib import Path

import yaml

from src.models.schemas import AlertRuleConfig

ALERTS_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "alerts.yaml"


def load_alert_rules(config_path: Path | None = None) -> list[AlertRuleConfig]:
    """Load alert rules from a YAML config file.

    Args:
        config_path: Path to the alerts YAML file. Defaults to config/alerts.yaml.

    Returns:
        List of validated AlertRuleConfig objects.
    """
    path = config_path or ALERTS_CONFIG_PATH

    if not path.exists():
        raise FileNotFoundError(f"Alerts config not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    rules = []
    for rule_data in raw.get("alerts", []):
        rules.append(AlertRuleConfig(**rule_data))

    return rules
