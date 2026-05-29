"""Unit tests for audit_report tool helpers.

Tests _parse_json_param and _build_definition_body in isolation.
"""
import json
import pytest

from altr_mcp.tools.audit_report import _build_definition_body, _parse_json_param


# ── _parse_json_param ────────────────────────────────────────────────────────

def test_parse_json_param_none():
    assert _parse_json_param(None) is None


def test_parse_json_param_dict_passthrough():
    d = {"channels": [{"type": "email"}]}
    assert _parse_json_param(d) is d


def test_parse_json_param_json_string():
    s = '{"filter_groups": []}'
    result = _parse_json_param(s)
    assert result == {"filter_groups": []}


def test_parse_json_param_json_string_complex():
    data = {"channels": [{"type": "email", "recipients": ["a@b.com"]}]}
    result = _parse_json_param(json.dumps(data))
    assert result == data


def test_parse_json_param_invalid_json_raises():
    with pytest.raises(json.JSONDecodeError):
        _parse_json_param("not-json{")


# ── _build_definition_body ───────────────────────────────────────────────────

def test_build_definition_body_minimal():
    body = _build_definition_body(
        name="My Report",
        integration_type="oltp",
        description=None,
        lookback_days=None,
        timezone=None,
        schedule_cron=None,
        schedule_enabled=None,
        schedule_timezone=None,
        delivery=None,
        filters=None,
    )
    assert body == {"name": "My Report", "integration_type": "oltp"}


def test_build_definition_body_description():
    body = _build_definition_body(
        name="R", integration_type="snowflake", description="desc",
        lookback_days=None, timezone=None, schedule_cron=None,
        schedule_enabled=None, schedule_timezone=None,
        delivery=None, filters=None,
    )
    assert body["description"] == "desc"


def test_build_definition_body_report_window_both():
    body = _build_definition_body(
        name="R", integration_type="oltp", description=None,
        lookback_days=7, timezone="America/Chicago",
        schedule_cron=None, schedule_enabled=None,
        schedule_timezone=None, delivery=None, filters=None,
    )
    assert body["report_window"] == {
        "lookback_days": 7, "timezone": "America/Chicago"
    }


def test_build_definition_body_report_window_only_lookback():
    body = _build_definition_body(
        name="R", integration_type="oltp", description=None,
        lookback_days=30, timezone=None,
        schedule_cron=None, schedule_enabled=None,
        schedule_timezone=None, delivery=None, filters=None,
    )
    assert body["report_window"] == {"lookback_days": 30}


def test_build_definition_body_report_window_only_timezone():
    body = _build_definition_body(
        name="R", integration_type="oltp", description=None,
        lookback_days=None, timezone="US/Eastern",
        schedule_cron=None, schedule_enabled=None,
        schedule_timezone=None, delivery=None, filters=None,
    )
    assert body["report_window"] == {"timezone": "US/Eastern"}


def test_build_definition_body_schedule_all_fields():
    body = _build_definition_body(
        name="R", integration_type="oltp", description=None,
        lookback_days=None, timezone=None,
        schedule_cron="0 12 * * ? *",
        schedule_enabled=True,
        schedule_timezone="America/New_York",
        delivery=None, filters=None,
    )
    assert body["schedule"] == {
        "cron": "0 12 * * ? *",
        "enabled": True,
        "timezone": "America/New_York",
    }


def test_build_definition_body_schedule_cron_only():
    body = _build_definition_body(
        name="R", integration_type="oltp", description=None,
        lookback_days=None, timezone=None,
        schedule_cron="0 9 ? * MON *",
        schedule_enabled=None, schedule_timezone=None,
        delivery=None, filters=None,
    )
    assert body["schedule"] == {"cron": "0 9 ? * MON *"}


def test_build_definition_body_delivery_as_dict():
    delivery = {"channels": [{"type": "email", "enabled": True,
                               "recipients": ["user@example.com"]}]}
    body = _build_definition_body(
        name="R", integration_type="oltp", description=None,
        lookback_days=None, timezone=None, schedule_cron=None,
        schedule_enabled=None, schedule_timezone=None,
        delivery=delivery, filters=None,
    )
    assert body["delivery"] == delivery


def test_build_definition_body_delivery_as_json_string():
    delivery = {"channels": []}
    body = _build_definition_body(
        name="R", integration_type="oltp", description=None,
        lookback_days=None, timezone=None, schedule_cron=None,
        schedule_enabled=None, schedule_timezone=None,
        delivery=json.dumps(delivery), filters=None,
    )
    assert body["delivery"] == delivery


def test_build_definition_body_filters_as_dict():
    filters = {"filter_groups": [{"filters": []}]}
    body = _build_definition_body(
        name="R", integration_type="oltp", description=None,
        lookback_days=None, timezone=None, schedule_cron=None,
        schedule_enabled=None, schedule_timezone=None,
        delivery=None, filters=filters,
    )
    assert body["filters"] == filters


def test_build_definition_body_no_extra_keys_when_optional_absent():
    body = _build_definition_body(
        name="X", integration_type="oltp", description=None,
        lookback_days=None, timezone=None, schedule_cron=None,
        schedule_enabled=None, schedule_timezone=None,
        delivery=None, filters=None,
    )
    assert set(body.keys()) == {"name", "integration_type"}
