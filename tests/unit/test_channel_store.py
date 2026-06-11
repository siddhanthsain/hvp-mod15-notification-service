import pytest
from fastapi.testclient import TestClient
from hvp_mod15_notification_service.main import app
from hvp_mod15_notification_service.services.channel_store import ChannelStore, DEFAULT_CHANNELS
from hvp_mod15_notification_service.schemas.channel import ChannelConfig


COORD_CONFIG = {
    "recipient_id":   "coord01",
    "recipient_type": "HOSPITAL_COORDINATOR",
    "channels":       ["EMAIL", "IN_APP"],
    "email":          "coord01@aiims.in",
    "phone":          None,
}

PATIENT_CONFIG = {
    "recipient_id":   "ABHA-1234567890",
    "recipient_type": "PATIENT",
    "channels":       ["SMS"],
    "email":          None,
    "phone":          "+919876543210",
}


@pytest.fixture(autouse=True)
def fresh_store():
    app.state.channel_store = ChannelStore()


@pytest.fixture
def store():
    return ChannelStore()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


# ── ChannelStore unit tests ───────────────────────────────────────────────────

def test_upsert_returns_channel_id(store):
    config = store.upsert(COORD_CONFIG)
    assert config["channel_id"].startswith("CHN-")


def test_upsert_sets_recipient_id(store):
    config = store.upsert(COORD_CONFIG)
    assert config["recipient_id"] == "coord01"


def test_upsert_sets_channels(store):
    config = store.upsert(COORD_CONFIG)
    assert "EMAIL"   in config["channels"]
    assert "IN_APP"  in config["channels"]


def test_upsert_same_recipient_updates_not_creates(store):
    store.upsert(COORD_CONFIG)
    store.upsert({**COORD_CONFIG, "email": "newemail@aiims.in"})
    assert store.count == 1


def test_upsert_updates_email(store):
    store.upsert(COORD_CONFIG)
    updated = store.upsert({**COORD_CONFIG, "email": "updated@aiims.in"})
    assert updated["email"] == "updated@aiims.in"


def test_upsert_increments_count(store):
    assert store.count == 0
    store.upsert(COORD_CONFIG)
    assert store.count == 1
    store.upsert(PATIENT_CONFIG)
    assert store.count == 2


def test_get_by_recipient_returns_config(store):
    store.upsert(COORD_CONFIG)
    config = store.get_by_recipient("coord01")
    assert config is not None
    assert config["recipient_type"] == "HOSPITAL_COORDINATOR"


def test_get_by_recipient_returns_none_for_unknown(store):
    assert store.get_by_recipient("nonexistent") is None


def test_list_by_type_filters_correctly(store):
    store.upsert(COORD_CONFIG)
    store.upsert(PATIENT_CONFIG)
    store.upsert({**COORD_CONFIG, "recipient_id": "coord02"})
    coordinators = store.list_by_type("HOSPITAL_COORDINATOR")
    assert len(coordinators) == 2
    assert all(c["recipient_type"] == "HOSPITAL_COORDINATOR" for c in coordinators)


def test_deactivate_sets_is_active_false(store):
    store.upsert(COORD_CONFIG)
    result = store.deactivate("coord01")
    assert result is True
    config = store.get_by_recipient("coord01")
    assert config["is_active"] is False


def test_deactivate_returns_false_for_unknown(store):
    assert store.deactivate("nobody") is False


def test_get_channels_for_recipient_returns_channels(store):
    store.upsert(COORD_CONFIG)
    channels = store.get_channels_for_recipient("coord01")
    assert "EMAIL"  in channels
    assert "IN_APP" in channels


def test_get_channels_for_unknown_returns_empty(store):
    assert store.get_channels_for_recipient("unknown") == []


def test_deactivated_recipient_returns_empty_channels(store):
    store.upsert(COORD_CONFIG)
    store.deactivate("coord01")
    assert store.get_channels_for_recipient("coord01") == []


def test_default_channels_defined():
    assert "HOSPITAL_COORDINATOR" in DEFAULT_CHANNELS
    assert "PATIENT"              in DEFAULT_CHANNELS
    assert "INSURER_ADJUDICATOR"  in DEFAULT_CHANNELS
    assert "SMS"   in DEFAULT_CHANNELS["PATIENT"]
    assert "EMAIL" in DEFAULT_CHANNELS["HOSPITAL_COORDINATOR"]


# ── Schema validation ─────────────────────────────────────────────────────────

def test_invalid_email_rejected():
    with pytest.raises(Exception):
        ChannelConfig(
            recipient_id="test", recipient_type="HOSPITAL_COORDINATOR",
            channels=["EMAIL"], email="notanemail",
        )


def test_invalid_phone_rejected():
    with pytest.raises(Exception):
        ChannelConfig(
            recipient_id="test", recipient_type="PATIENT",
            channels=["SMS"], phone="notaphone",
        )


def test_valid_email_accepted():
    c = ChannelConfig(
        recipient_id="test", recipient_type="HOSPITAL_COORDINATOR",
        channels=["EMAIL"], email="test@example.com",
    )
    assert c.email == "test@example.com"


# ── Routes ────────────────────────────────────────────────────────────────────

def test_upsert_channel_returns_201(client):
    resp = client.post("/api/v1/notifications/channels", json=COORD_CONFIG)
    assert resp.status_code == 201


def test_upsert_channel_returns_channel_id(client):
    resp = client.post("/api/v1/notifications/channels", json=COORD_CONFIG)
    assert "channel_id" in resp.json()


def test_get_channel_returns_200(client):
    client.post("/api/v1/notifications/channels", json=COORD_CONFIG)
    resp = client.get("/api/v1/notifications/channels/coord01")
    assert resp.status_code == 200


def test_get_unknown_channel_returns_404(client):
    assert client.get("/api/v1/notifications/channels/nobody").status_code == 404


def test_list_channels_returns_200(client):
    assert client.get("/api/v1/notifications/channels").status_code == 200


def test_list_by_type_filters(client):
    client.post("/api/v1/notifications/channels", json=COORD_CONFIG)
    client.post("/api/v1/notifications/channels", json=PATIENT_CONFIG)
    resp = client.get("/api/v1/notifications/channels?recipient_type=PATIENT")
    assert len(resp.json()) == 1
    assert resp.json()[0]["recipient_type"] == "PATIENT"


def test_deactivate_returns_204(client):
    client.post("/api/v1/notifications/channels", json=COORD_CONFIG)
    assert client.delete("/api/v1/notifications/channels/coord01").status_code == 204


def test_deactivate_unknown_returns_404(client):
    assert client.delete("/api/v1/notifications/channels/nobody").status_code == 404


def test_health_returns_200(client):
    assert client.get("/health").status_code == 200
