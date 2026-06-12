"""
Integration tests — full notify flow end-to-end.
All services wired together, no mocking of individual components.
"""

import pytest
from fastapi.testclient import TestClient
from hvp_mod15_notification_service.main import app
from hvp_mod15_notification_service.services.channel_store import ChannelStore
from hvp_mod15_notification_service.services.template_engine import TemplateEngine
from hvp_mod15_notification_service.services.provider import ProviderRegistry
from hvp_mod15_notification_service.services.dispatcher import Dispatcher
from hvp_mod15_notification_service.services.delivery_tracker import DeliveryTracker


@pytest.fixture(autouse=True)
def full_state():
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
            "recipient_id": "ABHA-INT-001",
            "recipient_type": "PATIENT",
            "channels": ["SMS"],
            "phone": "+919000000001",
        }
    )
    cs.upsert(
        {
            "recipient_id": "adj01",
            "recipient_type": "INSURER_ADJUDICATOR",
            "channels": ["IN_APP", "EMAIL"],
            "email": "adj01@insurer.in",
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


def test_full_claim_approved_flow(client):
    """claim.approved → coordinator gets EMAIL+IN_APP, patient gets SMS."""
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.approved",
            "source_module": "mod04",
            "event_payload": {
                "claim_id": "CLM-INT-001",
                "hospital_coordinator_id": "coord01",
                "patient_abha": "ABHA-INT-001",
                "approved_amount": "45000",
                "actor_name": "Dr. Priya",
                "insurer_code": "STAR_HEALTH",
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["dispatched_count"] == 3  # EMAIL + IN_APP + SMS
    assert data["delivered"] == 3
    assert len(data["notification_ids"]) == 3

    # Check delivery records
    deliveries = client.get("/api/v1/notifications/claim/CLM-INT-001").json()
    channels = {d["channel"] for d in deliveries}
    assert "EMAIL" in channels
    assert "IN_APP" in channels
    assert "SMS" in channels


def test_full_claim_rejected_flow(client):
    """claim.rejected → coordinator + patient both notified."""
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "claim.rejected",
            "source_module": "mod04",
            "event_payload": {
                "claim_id": "CLM-INT-002",
                "hospital_coordinator_id": "coord01",
                "patient_abha": "ABHA-INT-001",
                "rejection_reason": "Pre-existing condition not covered",
                "actor_name": "Coord01",
                "insurer_code": "NIVA_BUPA",
            },
        },
    )
    assert resp.json()["dispatched_count"] >= 2


def test_adjudicator_assignment_flow(client):
    """adjudicator.assigned → adjudicator gets IN_APP + EMAIL."""
    resp = client.post(
        "/api/v1/notifications/notify",
        json={
            "event_type": "adjudicator.assigned",
            "source_module": "mod06",
            "event_payload": {
                "claim_id": "CLM-INT-003",
                "adjudicator_id": "adj01",
                "hospital_code": "AIIMS_DEL",
                "claim_amount": "60000",
                "actor_name": "Adj01",
            },
        },
    )
    assert resp.json()["dispatched_count"] == 2  # IN_APP + EMAIL


def test_stats_reflect_all_flows(client):
    for event in ["claim.approved", "claim.rejected"]:
        client.post(
            "/api/v1/notifications/notify",
            json={
                "event_type": event,
                "source_module": "mod04",
                "event_payload": {
                    "claim_id": f"CLM-{event}",
                    "hospital_coordinator_id": "coord01",
                    "patient_abha": "ABHA-INT-001",
                    "approved_amount": "36000",
                    "actor_name": "Test",
                    "insurer_code": "TEST",
                    "rejection_reason": "Test",
                },
            },
        )
    stats = client.get("/api/v1/notifications/stats").json()
    assert stats["total"] >= 6
    assert stats["delivered"] >= 6
