"""
Shared pytest fixtures for MOD-15 Notification Service.
"""

import pytest
from fastapi.testclient import TestClient

from hvp_mod15_notification_service.main import app
from hvp_mod15_notification_service.services.channel_store import ChannelStore
from hvp_mod15_notification_service.services.template_engine import TemplateEngine
from hvp_mod15_notification_service.services.provider import ProviderRegistry
from hvp_mod15_notification_service.services.dispatcher import Dispatcher
from hvp_mod15_notification_service.services.delivery_tracker import DeliveryTracker


@pytest.fixture
def fresh_app():
    """App with clean state — no channels, empty tracker."""
    app.state.channel_store = ChannelStore()
    app.state.template_engine = TemplateEngine()
    app.state.provider_registry = ProviderRegistry(mock=True)
    app.state.dispatcher = Dispatcher()
    app.state.delivery_tracker = DeliveryTracker()
    return app


@pytest.fixture
def client(fresh_app):
    return TestClient(fresh_app, raise_server_exceptions=True)


@pytest.fixture
def seeded_client(fresh_app):
    """App with standard HVP recipients pre-configured."""
    fresh_app.state.channel_store.upsert(
        {
            "recipient_id": "coord01",
            "recipient_type": "HOSPITAL_COORDINATOR",
            "channels": ["EMAIL", "IN_APP"],
            "email": "coord01@aiims.in",
        }
    )
    fresh_app.state.channel_store.upsert(
        {
            "recipient_id": "ABHA-123456",
            "recipient_type": "PATIENT",
            "channels": ["SMS"],
            "phone": "+919876543210",
        }
    )
    fresh_app.state.channel_store.upsert(
        {
            "recipient_id": "adj01",
            "recipient_type": "INSURER_ADJUDICATOR",
            "channels": ["IN_APP", "EMAIL"],
            "email": "adj01@starhealth.in",
        }
    )
    return TestClient(fresh_app, raise_server_exceptions=True)
