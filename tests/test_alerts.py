"""Tests for the alert system."""

import pytest

from src.alerts.rules import load_alert_rules


class TestAlertRules:
    """Tests for alert rule loading and validation."""

    def test_load_default_rules(self):
        """Verify config/alerts.yaml loads successfully."""
        rules = load_alert_rules()
        assert len(rules) == 5
        assert rules[0].id == "cpc_spike"

    def test_rule_ids_unique(self):
        """All alert rule IDs must be unique."""
        rules = load_alert_rules()
        ids = [r.id for r in rules]
        assert len(ids) == len(set(ids))

    def test_severity_values(self):
        """All severities must be valid enum values."""
        rules = load_alert_rules()
        valid = {"low", "medium", "high", "critical"}
        for rule in rules:
            assert rule.severity.value in valid


class TestAlertEngine:
    """Tests for the alert evaluation engine."""

    @pytest.mark.skip(reason="Engine not yet implemented (Phase 4)")
    def test_evaluate_cpc_spike(self):
        pass

    @pytest.mark.skip(reason="Engine not yet implemented (Phase 4)")
    def test_cooldown_period(self):
        pass
