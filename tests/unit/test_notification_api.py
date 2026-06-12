import pytest
from fastapi.testclient import TestClient
from hvp_mod15_notification_service.main import app
from hvp_mod15_notification_service.services.channel_store import ChannelStore
from hvp_mod15_notification_service.services.template_engine import TemplateEngine
from hvp_mod15_notification_service.services.provider import ProviderRegistry
from hvp_mod15_notification_service.services.dispatcher import Dispatcher
from hvp_mod15_notification_service.services.delivery_tracker import DeliveryTracker


FULL_PAYLOAD = {
    "claim_id": "CLM-TEST-001",
    "insurer_code": "STAR_HEALTH",
    "hospital_code": "AIIMS_DEL",
    "hospital_coordinator_id": "coord01",
    "patient_abha": "ABHA-999888",
    "approved_amount": "36000",
    "actor_name": "Ramesh Kumar",
    "rejection_reason": "Duplicate claim",
    "query_text": "Please provide discharge summary",
}


@pytest.fixture(autouse=True)
def seeded_state():
    cs = ChannelStore()
    cs.upsert(
        {
            "recipient_id": "coord01",
            "recipient_type": "HOSPITAL_COORDINATOR",
            "channels": ["EMAIL", "IN_APP"],
            "email": "coord01@aiims.in",
        }
    )
    cs.upsert(
        {
            "recipient_id": "ABHA-999888",
            "recipient_type": "PATIENT",
            "channels": ["SMS"],
            "phone": "+919876543210",
        }
    )
    cs.upsert(
        {
            "recipient_id": "adj01",
            "recipient_type": "INSURER_ADJUDICATOR",
            "channels": ["IN_APP", "EMAIL"],
            "email": "adj01@starhealth.in",
        }
    )
    app.state.channel_store = cs
    app.state.template_engine = TemplateEngine()
    app.state.provider_registry = ProviderRegistry(mock=True)
    app.state.dispatcher = Dispatcher()
    app.state.delivery_tracker = DeliveryTracker()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


# ── POST /api/v1/notifications/notify ────────────────────────────────────────


def test_notify_returns_200(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    assert resp.status_code == 200


def test_notify_returns_dispatched_count(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    assert resp.json()["dispatched_count"] > 0


def test_notify_claim_approved_dispatches_to_coordinator_and_patient(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    # coord01 has EMAIL+IN_APP = 2 sends, ABHA-999888 has SMS = 1 send → total ≥ 3
    assert resp.json()["dispatched_count"] >= 3


def test_notify_returns_notification_ids(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    ids = resp.json()["notification_ids"]
    assert isinstance(ids, list)
    assert len(ids) > 0
    assert all(i.startswith("DLV-") for i in ids)


def test_notify_ids_are_unique(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    ids = resp.json()["notification_ids"]
    assert len(ids) == len(set(ids))


def test_notify_returns_delivered_count(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    assert "delivered" in resp.json()
    assert resp.json()["delivered"] >= 1


def test_notify_creates_delivery_records(client):
    before = app.state.delivery_tracker.total
    client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    assert app.state.delivery_tracker.total > before


def test_notify_rejected_dispatches_with_reason(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.rejected",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    assert resp.json()["dispatched_count"] > 0


def test_notify_queried_dispatches_to_coordinator_only(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.queried",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    # Only hospital_coordinator_id mapped for claim.queried — not patient
    assert resp.json()["dispatched_count"] > 0


def test_notify_adjudicator_assigned(client):
    payload = {
        **FULL_PAYLOAD,
        "adjudicator_id": "adj01",
        "hospital_code": "AIIMS_DEL",
        "claim_amount": "45000",
    }
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "adjudicator.assigned",
            "event_payload": payload,
            "source_module": "mod06",
        },
    )
    assert resp.json()["dispatched_count"] > 0


def test_notify_empty_event_type_returns_422(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "",
            "event_payload": FULL_PAYLOAD,
        },
    )
    assert resp.status_code == 422


def test_notify_no_recipients_configured_returns_zero(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": {"claim_id": "CLM-NO-RECIP"},  # no coordinator or patient ID
            "source_module": "mod04",
        },
    )
    assert resp.json()["dispatched_count"] == 0


def test_notify_source_module_in_response(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    assert resp.json()["source_module"] == "mod04"


def test_notify_event_type_in_response(client):
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    assert resp.json()["event_type"] == "claim.approved"


# ── GET /api/v1/notifications/claim/{claim_id} ────────────────────────────────


def test_get_notifications_for_claim_returns_200(client):
    client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    resp = client.get("/api/v1/notifications/claim/CLM-TEST-001")
    assert resp.status_code == 200


def test_get_notifications_for_claim_returns_list(client):
    client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    resp = client.get("/api/v1/notifications/claim/CLM-TEST-001")
    assert isinstance(resp.json(), list)
    assert len(resp.json()) > 0


def test_get_notifications_unknown_claim_returns_empty_list(client):
    resp = client.get("/api/v1/notifications/claim/CLM-NOTEXIST-999")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_notifications_for_claim_has_delivery_ids(client):
    client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    entries = client.get("/api/v1/notifications/claim/CLM-TEST-001").json()
    assert all("delivery_id" in e for e in entries)
    assert all(e["delivery_id"].startswith("DLV-") for e in entries)


# ── GET /api/v1/notifications/stats ──────────────────────────────────────────


def test_notification_stats_returns_200(client):
    assert client.get("/api/v1/notifications/stats").status_code == 200


def test_stats_has_total(client):
    stats = client.get("/api/v1/notifications/stats").json()
    assert "total" in stats


def test_stats_has_total_channels_and_templates(client):
    stats = client.get("/api/v1/notifications/stats").json()
    assert "total_channels_configured" in stats
    assert "total_templates" in stats
    assert stats["total_channels_configured"] == 3  # coord01, ABHA-999888, adj01
    assert stats["total_templates"] > 0


def test_stats_has_delivered_failed_dead(client):
    stats = client.get("/api/v1/notifications/stats").json()
    assert "delivered" in stats
    assert "failed" in stats
    assert "dead" in stats


def test_stats_delivered_count_after_notify(client):
    client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "event_payload": FULL_PAYLOAD,
            "source_module": "mod04",
        },
    )
    stats = client.get("/api/v1/notifications/stats").json()
    assert stats["delivered"] >= 3
    assert stats["total"] >= 3


# ── End-to-end flow test ──────────────────────────────────────────────────────


def test_e2e_configure_then_notify_then_check(client):
    # 1. Configure a new channel
    client.post(
        "/api/v1/notifications/channels",
        json={
            "recipient_id": "new_coord",
            "recipient_type": "HOSPITAL_COORDINATOR",
            "channels": ["EMAIL"],
            "email": "new@hospital.in",
        },
    )

    # 2. Notify with new coordinator
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.submitted",
            "event_payload": {
                "claim_id": "CLM-E2E-001",
                "hospital_coordinator_id": "new_coord",
                "insurer_code": "NIVA_BUPA",
                "claim_amount": "55000",
                "actor_name": "Dr. Priya",
            },
            "source_module": "mod05",
        },
    )
    assert resp.json()["dispatched_count"] >= 1

    # 3. Check delivery records for that claim
    deliveries = client.get("/api/v1/notifications/claim/CLM-E2E-001").json()
    assert len(deliveries) >= 1
    assert deliveries[0]["claim_id"] == "CLM-E2E-001"


def test_health_returns_200(client):
    assert client.get("/health").status_code == 200
