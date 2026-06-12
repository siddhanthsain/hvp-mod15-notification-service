import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .routes.channels  import router as channels_router
from .routes.templates import router as templates_router
from .routes.dispatch  import router as dispatch_router
from .services.channel_store   import ChannelStore
from .services.template_engine  import TemplateEngine
from .services.provider         import ProviderRegistry
from .services.dispatcher       import Dispatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MOD-15 Notification Service starting...")
    app.state.channel_store   = ChannelStore()
    app.state.template_engine  = TemplateEngine()
    app.state.provider_registry = ProviderRegistry(mock=True)
    app.state.dispatcher        = Dispatcher()
    logger.info("Channel store initialised")
    logger.info("MOD-15 READY")
    yield
    logger.info("MOD-15 shutting down")


app = FastAPI(
    title="HVP MOD-15 Notification Service",
    version="0.1.0",
    description=(
        "Multi-channel notification service for HVP. "
        "SMS, Email, WhatsApp, In-app. "
        "Called by MOD-04, MOD-05, MOD-06."
    ),
    lifespan=lifespan,
)
app.include_router(channels_router)
app.include_router(templates_router)
app.include_router(dispatch_router)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "module": "MOD-15"}
