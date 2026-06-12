import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .routes.channels import router as channels_router
from .routes.templates import router as templates_router
from .routes.dispatch import router as dispatch_router
from .routes.deliveries import router as deliveries_router
from .routes.notify import router as notify_router
from .services.channel_store import ChannelStore
from .services.template_engine import TemplateEngine
from .services.provider import ProviderRegistry
from .services.dispatcher import Dispatcher
from .services.delivery_tracker import DeliveryTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MOD-15 Notification Service starting...")
    app.state.channel_store = ChannelStore()
    app.state.template_engine = TemplateEngine()
    app.state.provider_registry = ProviderRegistry(mock=True)
    app.state.dispatcher = Dispatcher()
    app.state.delivery_tracker = DeliveryTracker()
    logger.info("Templates loaded: %s", app.state.template_engine.total_templates)
    logger.info("MOD-15 READY | port 8015")
    yield
    logger.info("MOD-15 shutting down")


app = FastAPI(
    title="HVP MOD-15 Notification Service",
    version="0.1.0",
    description=(
        "Multi-channel notification service for HVP. "
        "SMS, Email, WhatsApp, In-app alerts for claim events. "
        "Called by MOD-04 (claim events), MOD-05 (patient alerts), "
        "MOD-06 (adjudicator assignments)."
    ),
    lifespan=lifespan,
)
app.include_router(notify_router)  # Primary endpoint first
app.include_router(channels_router)
app.include_router(templates_router)
app.include_router(dispatch_router)
app.include_router(deliveries_router)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "module": "MOD-15"}
