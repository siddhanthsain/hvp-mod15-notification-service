import pytest
from fastapi.testclient import TestClient
from hvp_mod15_notification_service.main import app
from hvp_mod15_notification_service.services.channel_store     import ChannelStore
from hvp_mod15_notification_service.services.template_engine   import TemplateEngine
from hvp_mod15_notification_service.services.provider          import ProviderRegistry
from hvp_mod15_notification_service.services.dispatcher        import Dispatcher
from hvp_mod15_notification_service.services.delivery_tracker  import DeliveryTracker, MAX_RETRIES


SAMPLE_DISPATCH = {
    "event_type":   "claim.approved",
    "recipient_id": "coord01",
    "channel":      "EMAIL",
    "contact":      "coord01@aiims.in",
    "claim_id":     "CLM-001",
    "success":      True,
    "provider_id":  "MOCK-000001",
}


@pytest.fixture(autouse=True)
def fresh_state():
    cs = ChannelStore()
    cs.upsert({"recipient_id":"coord01","recipient_type":"HOSPITAL_COORDINATOR",
               "channels":["EMAIL","IN_APP"],"email":"coord01@aiims.in"})
    cs.upsert({"recipient_id":"ABHA-123456","recipient_type":"PATIENT",
               "channels":["SMS"],"phone":"+919876543210"})
    app.state.channel_store    = cs
    app.state.template_engine  = TemplateEngine()
    app.state.provider_registry = ProviderRegistry(mock=True)
    app.state.dispatcher       = Dispatcher()
    app.state.delivery_tracker = DeliveryTracker()


@pytest.fixture
def tracker():
    return DeliveryTracker()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


# ── DeliveryTracker unit tests ────────────────────────────────────────────────

def test_record_returns_delivery_id(tracker):
    d = tracker.record(SAMPLE_DISPATCH)
    assert d["delivery_id"].startswith("DLV-")


def test_record_delivered_when_success_true(tracker):
    d = tracker.record(SAMPLE_DISPATCH)
    assert d["status"] == "DELIVERED"


def test_record_failed_when_success_false(tracker):
    d = tracker.record({**SAMPLE_DISPATCH, "success": False})
    assert d["status"] == "FAILED"


def test_record_increments_total(tracker):
    assert tracker.total == 0
    tracker.record(SAMPLE_DISPATCH)
    assert tracker.total == 1


def test_record_sets_all_fields(tracker):
    d = tracker.record(SAMPLE_DISPATCH)
    assert d["event_type"]   == "claim.approved"
    assert d["recipient_id"] == "coord01"
    assert d["channel"]      == "EMAIL"
    assert d["claim_id"]     == "CLM-001"


def test_mark_failed_increments_retry_count(tracker):
    d  = tracker.record(SAMPLE_DISPATCH)
    tracker.mark_failed(d["delivery_id"], "Connection refused")
    updated = tracker.get(d["delivery_id"])
    assert updated["retry_count"] == 1


def test_mark_failed_max_retries_sets_dead(tracker):
    d = tracker.record(SAMPLE_DISPATCH)
    for _ in range(MAX_RETRIES):
        tracker.mark_failed(d["delivery_id"], "Failed")
    dead = tracker.get(d["delivery_id"])
    assert dead["status"] == "DEAD"


def test_mark_delivered_changes_status(tracker):
    d = tracker.record({**SAMPLE_DISPATCH, "success": False})
    tracker.mark_delivered(d["delivery_id"])
    assert tracker.get(d["delivery_id"])["status"] == "DELIVERED"


def test_mark_failed_returns_none_for_missing(tracker):
    assert tracker.mark_failed("DLV-NOTEXIST", "err") is None


def test_get_returns_delivery(tracker):
    d       = tracker.record(SAMPLE_DISPATCH)
    fetched = tracker.get(d["delivery_id"])
    assert fetched["recipient_id"] == "coord01"


def test_get_returns_none_for_missing(tracker):
    assert tracker.get("DLV-NOTEXIST") is None


def test_list_all_filters_by_status(tracker):
    tracker.record(SAMPLE_DISPATCH)
    tracker.record({**SAMPLE_DISPATCH, "success": False, "claim_id": "CLM-002"})
    delivered = tracker.list_all(status="DELIVERED")
    failed    = tracker.list_all(status="FAILED")
    assert len(delivered) == 1
    assert len(failed)    == 1


def test_list_all_filters_by_channel(tracker):
    tracker.record(SAMPLE_DISPATCH)
    tracker.record({**SAMPLE_DISPATCH, "channel": "SMS", "claim_id": "CLM-002"})
    emails = tracker.list_all(channel="EMAIL")
    assert len(emails) == 1


def test_list_all_filters_by_claim_id(tracker):
    tracker.record(SAMPLE_DISPATCH)
    tracker.record({**SAMPLE_DISPATCH, "claim_id": "CLM-002"})
    results = tracker.list_all(claim_id="CLM-001")
    assert len(results) == 1


def test_stats_returns_correct_counts(tracker):
    tracker.record(SAMPLE_DISPATCH)
    tracker.record(SAMPLE_DISPATCH)
    tracker.record({**SAMPLE_DISPATCH, "success": False})
    stats = tracker.stats()
    assert stats["total"]     == 3
    assert stats["delivered"] == 2
    assert stats["failed"]    == 1


def test_stats_by_channel(tracker):
    tracker.record(SAMPLE_DISPATCH)
    tracker.record({**SAMPLE_DISPATCH, "channel": "SMS"})
    stats = tracker.stats()
    assert stats["by_channel"]["EMAIL"] == 1
    assert stats["by_channel"]["SMS"]   == 1


def test_max_retries_constant():
    assert MAX_RETRIES == 3


# ── Integration: dispatch creates delivery records ────────────────────────────

def test_dispatch_creates_delivery_records(client):
    resp = client.post("/api/v1/notifications/dispatch", json={
        "event_type":    "claim.approved",
        "event_payload": {
            "claim_id": "CLM-001", "insurer_code": "STAR_HEALTH",
            "hospital_coordinator_id": "coord01", "patient_abha": "ABHA-123456",
            "approved_amount": "36000", "actor_name": "Ramesh",
        },
    })
    assert resp.json()["dispatched_count"] > 0
    assert app.state.delivery_tracker.total > 0


# ── Route tests ───────────────────────────────────────────────────────────────

def test_list_deliveries_returns_200(client):
    assert client.get("/api/v1/notifications/deliveries").status_code == 200


def test_delivery_stats_returns_200(client):
    assert client.get("/api/v1/notifications/deliveries/stats").status_code == 200


def test_delivery_stats_has_required_fields(client):
    stats = client.get("/api/v1/notifications/deliveries/stats").json()
    assert "total"     in stats
    assert "delivered" in stats
    assert "failed"    in stats
    assert "dead"      in stats


def test_get_delivery_404_for_unknown(client):
    assert client.get("/api/v1/notifications/deliveries/DLV-NOTEXIST").status_code == 404
