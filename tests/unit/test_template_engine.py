import pytest
from fastapi.testclient import TestClient
from hvp_mod15_notification_service.main import app
from hvp_mod15_notification_service.services.channel_store   import ChannelStore
from hvp_mod15_notification_service.services.template_engine import (
    TemplateEngine, BUILTIN_TEMPLATES
)


@pytest.fixture(autouse=True)
def fresh_state():
    app.state.channel_store   = ChannelStore()
    app.state.template_engine = TemplateEngine()


@pytest.fixture
def engine():
    return TemplateEngine()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


# ── Built-in templates ────────────────────────────────────────────────────────

def test_builtin_templates_seeded(engine):
    assert engine.total_templates == len(BUILTIN_TEMPLATES)


def test_claim_approved_sms_template_exists(engine):
    tpl = engine.get_template("claim.approved", "SMS")
    assert tpl is not None


def test_claim_approved_email_template_exists(engine):
    tpl = engine.get_template("claim.approved", "EMAIL")
    assert tpl is not None


def test_claim_rejected_template_exists(engine):
    assert engine.get_template("claim.rejected", "SMS")    is not None
    assert engine.get_template("claim.rejected", "EMAIL")  is not None
    assert engine.get_template("claim.rejected", "IN_APP") is not None


def test_claim_queried_templates_exist(engine):
    assert engine.get_template("claim.queried", "SMS") is not None


def test_adjudicator_assigned_templates_exist(engine):
    assert engine.get_template("adjudicator.assigned", "EMAIL")  is not None
    assert engine.get_template("adjudicator.assigned", "IN_APP") is not None


def test_unknown_event_type_returns_none(engine):
    assert engine.get_template("unknown.event", "SMS") is None


# ── render ────────────────────────────────────────────────────────────────────

def test_render_substitutes_variables(engine):
    result = engine.render("claim.approved", "SMS", {
        "claim_id": "CLM-001", "approved_amount": "36000"
    })
    assert result is not None
    assert "CLM-001" in result["body"]
    assert "36000"   in result["body"]


def test_render_returns_subject_for_email(engine):
    result = engine.render("claim.approved", "EMAIL", {
        "actor_name": "Ramesh", "claim_id": "CLM-001", "approved_amount": "36000"
    })
    assert result["subject"] is not None
    assert "CLM-001" in result["subject"]


def test_render_subject_none_for_sms(engine):
    result = engine.render("claim.approved", "SMS", {"claim_id": "CLM-001", "approved_amount": "36000"})
    assert result["subject"] is None


def test_render_missing_variables_substituted_safely(engine):
    # Missing variables should not raise — use {key} placeholder
    result = engine.render("claim.approved", "IN_APP", {})
    assert result is not None
    assert "body" in result


def test_render_returns_none_for_unknown_event(engine):
    assert engine.render("no.such.event", "SMS", {}) is None


def test_render_returns_template_id(engine):
    result = engine.render("claim.approved", "SMS",
                           {"claim_id": "CLM-001", "approved_amount": "36000"})
    assert "template_id" in result
    assert result["template_id"].startswith("TPL-")


def test_render_rejected_includes_reason(engine):
    result = engine.render("claim.rejected", "SMS", {
        "claim_id": "CLM-001", "rejection_reason": "Duplicate claim"
    })
    assert "Duplicate claim" in result["body"]


def test_render_queried_includes_query_text(engine):
    result = engine.render("claim.queried", "IN_APP", {
        "claim_id": "CLM-001", "query_text": "Please provide discharge summary"
    })
    assert "discharge summary" in result["body"]


# ── add_template ──────────────────────────────────────────────────────────────

def test_add_custom_template(engine):
    tpl = engine.add_template({
        "event_type": "custom.event",
        "channel":    "SMS",
        "body":       "Custom: {param1}",
    })
    assert tpl["template_id"].startswith("TPL-")
    assert engine.total_templates == len(BUILTIN_TEMPLATES) + 1


def test_add_template_cannot_override_builtin(engine):
    with pytest.raises(ValueError, match="built-in"):
        engine.add_template({
            "event_type": "claim.approved",
            "channel":    "SMS",
            "body":       "Override attempt",
        })


def test_list_by_event_type(engine):
    templates = engine.list_by_event_type("claim.approved")
    assert len(templates) >= 3  # SMS, EMAIL, IN_APP
    assert all(t["event_type"] == "claim.approved" for t in templates)


# ── Routes ────────────────────────────────────────────────────────────────────

def test_list_templates_returns_200(client):
    resp = client.get("/api/v1/notifications/templates")
    assert resp.status_code == 200
    assert len(resp.json()) == len(BUILTIN_TEMPLATES)


def test_get_templates_for_event_returns_200(client):
    resp = client.get("/api/v1/notifications/templates/claim.approved")
    assert resp.status_code == 200
    assert len(resp.json()) >= 3


def test_add_custom_template_returns_201(client):
    resp = client.post("/api/v1/notifications/templates", json={
        "event_type": "custom.test",
        "channel":    "SMS",
        "body":       "Test message: {param}",
    })
    assert resp.status_code == 201


def test_override_builtin_returns_409(client):
    resp = client.post("/api/v1/notifications/templates", json={
        "event_type": "claim.approved",
        "channel":    "SMS",
        "body":       "Attempt override",
    })
    assert resp.status_code == 409


def test_render_endpoint_returns_200(client):
    resp = client.post("/api/v1/notifications/templates/render", json={
        "event_type": "claim.approved",
        "channel":    "SMS",
        "variables":  {"claim_id": "CLM-001", "approved_amount": "36000"},
    })
    assert resp.status_code == 200
    assert "CLM-001" in resp.json()["body"]


def test_render_unknown_event_returns_404(client):
    resp = client.post("/api/v1/notifications/templates/render", json={
        "event_type": "no.event",
        "channel":    "SMS",
        "variables":  {},
    })
    assert resp.status_code == 404


def test_invalid_channel_returns_422(client):
    resp = client.post("/api/v1/notifications/templates/render", json={
        "event_type": "claim.approved",
        "channel":    "TELEGRAM",
        "variables":  {},
    })
    assert resp.status_code == 422
