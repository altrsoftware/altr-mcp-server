"""Tests for Pydantic input validation models."""
import pytest
from pydantic import ValidationError

from altr_mcp.models import (
    MaskingRule,
    validate_masking_rules,
    SidecarBinding,
    validate_access_rate_thresholds,
    validate_time_window_thresholds,
)


def test_masking_rule_valid():
    rule = MaskingRule(
        masking_policy=10001,
        role="ANALYST",
        tag_value="PII_SSN")
    assert rule.masking_policy == 10001


def test_masking_rule_out_of_range():
    with pytest.raises(ValidationError):
        MaskingRule(masking_policy=999, role="ANALYST", tag_value="PII_SSN")


def test_masking_rule_missing_role():
    with pytest.raises(ValidationError):
        MaskingRule(masking_policy=10001, tag_value="PII_SSN")


def test_validate_masking_rules_valid():
    result = validate_masking_rules(
        [{"masking_policy": 10001, "role": "A", "tag_value": "B"}])
    assert result is None


def test_validate_masking_rules_invalid():
    result = validate_masking_rules([{"masking_policy": "bad"}])
    assert result is not None
    assert "rules[0]" in result


def test_validate_masking_rules_empty():
    result = validate_masking_rules([])
    assert result == "No rules provided"


def test_sidecar_binding_valid():
    b = SidecarBinding(port=5432, repo_name="myrepo")
    assert b.port == 5432


def test_sidecar_binding_invalid_port():
    with pytest.raises(ValidationError):
        SidecarBinding(port=0, repo_name="myrepo")


def test_existing_access_rate_threshold():
    result = validate_access_rate_thresholds(
        [{"access_rate_unit": "HOUR", "access_rate_limit": 100, "action": "ALERT"}])
    assert result is None


def test_existing_time_window_threshold():
    result = validate_time_window_thresholds([{
        "day": ["MONDAY"], "start_time": {"hour": 9, "minute": 0},
        "end_time": {"hour": 17, "minute": 0}, "timezone": "UTC", "action": "ALERT"
    }])
    assert result is None
