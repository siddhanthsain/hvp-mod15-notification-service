import pytest
from fastapi.testclient import TestClient
from hvp_mod15_notification_service.main import app
from hvp_mod15_notification_service.services.channel_store    import ChannelStore
from hvp_mod15_notification_service.services.template_engine  import TemplateEngine
from hvp_mod15_notification_service.services.provider         import ProviderRegistry, MockProvider
from hvp_mod15_notification_service.services.dispatcher       import Dispatcher, EVENT_RECIPIENT_MAP


COORD_CHANNEL = {
    "recipient_id":   "coord01",
    "recipient_type": "HOSPITAL_COORDINATOR",
    "channels":       ["EMAIL", "IN_APP"],
    "email":          "coord01@aiims.in",
}

PATIENT_CHANNEL = {
    "recipient_id":   "ABHA-123456",
    "recipient_type": "PATIENT",
    "channels":       ["SMS"],
    "phone":          "+919876543210",
}

APPROVED_PAYLOAD = {
    "claim_id":               "CLM-001",
    "insurer_code":           "STAR_HEALTH",
    "hospital_coordinator_id": "coord01",
    "patient_abha":           "ABHA-123456",
    "approved_amount":        "36000",
    "actor_name":             "Ramesh Kumar",
}


@pytest.fixture(autouse=True)
def seeded_state():
    cs = ChannelStore()
    cs.upsert(COORD_CHANNEL)
    cs.upsert(PATIENT_CHANNEL)
    app.state.channel_store    = cs
    app.state.template_engine  = TemplateEngine()
    app.state.provider_registry = ProviderRegistry(mock=True)
    app.state.dispatcher       = Dispatcher()


@pytest.fixture
def dispatcher():
    return Dispatcher()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


# ── Dispatcher unit tests ─────────────────────────────────────────────────────

def test_dispatch_returns_results_list(dispatcher):
    cs  = ChannelStore()
    cs.upsert(COORD_CHANNEL)
    te  = TemplateEngine()
    pr  = ProviderRegistry(mock=True)
    results = dispatcher.dispatch("claim.approved", APPROVED_PAYLOAD, cs, te, pr)
    assert isinstance(results, list)


def test_dispatch_approved_sends_to_coordinator(dispatcher):
    cs = ChannelStore()
    cs.upsert(COORD_CHANNEL)
    cs.upsert(PATIENT_CHANNEL)
    te  = TemplateEngine()
    pr  = ProviderRegistry(mock=True)
    results = dispatcher.dispatch("claim.approved", APPROVED_PAYLOAD, cs, te, pr)
    recipient_ids = [r["recipient_id"] for r in results]
    assert "coord01" in recipient_ids


def test_dispatch_approved_sends_to_patient(dispatcher):
    cs = ChannelStore()
    cs.upsert(COORD_CHANNEL)
    cs.upsert(PATIENT_CHANNEL)
    te  = TemplateEngine()
    pr  = ProviderRegistry(mock=True)
    results = dispatcher.dispatch("claim.approved", APPROVED_PAYLOAD, cs, te, pr)
    recipient_ids = [r["recipient_id"] for r in results]
    assert "ABHA-123456" in recipient_ids


def test_dispatch_sends_sms_to_patient(dispatcher):
    cs = ChannelStore()
    cs.upsert(PATIENT_CHANNEL)
    te  = TemplateEngine()
    pr  = ProviderRegistry(mock=True)
    payload = {**APPROVED_PAYLOAD, "hospital_coordinator_id": None}
    results = dispatcher.dispatch("claim.approved", payload, cs, te, pr)
    sms_sends = [r for r in results if r["channel"] == "SMS"]
    assert len(sms_sends) >= 1


def test_dispatch_sends_email_to_coordinator(dispatcher):
    cs = ChannelStore()
    cs.upsert(COORD_CHANNEL)
    te  = TemplateEngine()
    pr  = ProviderRegistry(mock=True)
    payload = {**APPROVED_PAYLOAD, "patient_abha": None}
    results = dispatcher.dispatch("claim.approved", payload, cs, te, pr)
    email_sends = [r for r in results if r["channel"] == "EMAIL"]
    assert len(email_sends) >= 1


def test_dispatch_no_recipients_returns_empty(dispatcher):
    cs = ChannelStore()  # empty
    te = TemplateEngine()
    pr = ProviderRegistry(mock=True)
    results = dispatcher.dispatch("claim.approved", {}, cs, te, pr)
    assert results == []


def test_dispatch_increments_mock_sent_count(dispatcher):
    cs = ChannelStore()
    cs.upsert(COORD_CHANNEL)
    te = TemplateEngine()
    pr = ProviderRegistry(mock=True)
    payload = {**APPROVED_PAYLOAD, "patient_abha": None}
    before = pr.mock_provider.sent_count
    dispatcher.dispatch("claim.approved", payload, cs, te, pr)
    assert pr.mock_provider.sent_count > before


def test_dispatch_result_has_required_fields(dispatcher):
    cs = ChannelStore()
    cs.upsert(COORD_CHANNEL)
    te = TemplateEngine()
    pr = ProviderRegistry(mock=True)
    payload = {**APPROVED_PAYLOAD, "patient_abha": None}
    results = dispatcher.dispatch("claim.approved", payload, cs, te, pr)
    for r in results:
        assert "event_type"    in r
        assert "recipient_id"  in r
        assert "channel"       in r
        assert "success"       in r
        assert "dispatched_at" in r


def test_dispatch_result_success_is_true(dispatcher):
    cs = ChannelStore()
    cs.upsert(COORD_CHANNEL)
    te = TemplateEngine()
    pr = ProviderRegistry(mock=True)
    payload = {**APPROVED_PAYLOAD, "patient_abha": None}
    results = dispatcher.dispatch("claim.approved", payload, cs, te, pr)
    assert all(r["success"] is True for r in results)


def test_event_recipient_map_has_claim_events():
    assert "claim.approved"  in EVENT_RECIPIENT_MAP
    assert "claim.rejected"  in EVENT_RECIPIENT_MAP
    assert "claim.submitted" in EVENT_RECIPIENT_MAP
    assert "claim.queried"   in EVENT_RECIPIENT_MAP


# ── MockProvider tests ────────────────────────────────────────────────────────

def test_mock_provider_records_send():
    mock = MockProvider()
    mock.send("SMS", "+91987654321", None, "Test message")
    assert mock.sent_count == 1


def test_mock_provider_get_sent_by_channel():
    mock = MockProvider()
    mock.send("SMS",   "+91987654321", None,         "SMS msg")
    mock.send("EMAIL", "test@test.com", "Subject", "Email msg")
    assert len(mock.get_sent("SMS")) == 1
    assert len(mock.get_sent("EMAIL")) == 1


def test_mock_provider_returns_provider_id():
    mock   = MockProvider()
    result = mock.send("SMS", "+91987654321", None, "Test")
    assert "provider_id" in result
    assert result["provider_id"].startswith("MOCK-")


# ── Route tests ───────────────────────────────────────────────────────────────

def test_dispatch_endpoint_returns_200(client):
    resp = client.post("/api/v1/notifications/dispatch", json={
        "event_type":    "claim.approved",
        "event_payload": APPROVED_PAYLOAD,
    })
    assert resp.status_code == 200


def test_dispatch_endpoint_returns_dispatched_count(client):
    resp = client.post("/api/v1/notifications/dispatch", json={
        "event_type":    "claim.approved",
        "event_payload": APPROVED_PAYLOAD,
    })
    assert "dispatched_count" in resp.json()
    assert resp.json()["dispatched_count"] > 0


def test_dispatch_endpoint_returns_results_list(client):
    resp = client.post("/api/v1/notifications/dispatch", json={
        "event_type":    "claim.approved",
        "event_payload": APPROVED_PAYLOAD,
    })
    assert isinstance(resp.json()["results"], list)
