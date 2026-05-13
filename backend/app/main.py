from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.v1.router import api_router
import traceback

from contextlib import asynccontextmanager
from app.core.cache import init_redis, close_redis
from app.core.pubsub import pubsub_service
import asyncio
import sentry_sdk
import os

# Initialize Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_redis()
    asyncio.create_task(pubsub_service.start_listener())
    yield
    # Shutdown
    await pubsub_service.stop_listener()
    await close_redis()


app=FastAPI(
    title="Dispose API",
    version="0.1.0",
    description="API for Dispose ",
    lifespan=lifespan
)

# Initialize Prometheus Instrumentator
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

app.include_router(api_router,prefix="/api/v1")



@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": str(exc)})