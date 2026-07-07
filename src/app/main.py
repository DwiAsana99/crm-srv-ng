import time
import uuid
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.limiter import limiter
from app.api.v1.router import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("crm")

_cors_origins = (
    ["http://localhost", "http://localhost:3000", "http://127.0.0.1"]
    if settings.ENV == "dev" and not settings.CORS_ORIGINS
    else [str(o) for o in settings.CORS_ORIGINS]
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    default_response_class=ORJSONResponse,
    docs_url="/docs" if settings.ENV == "dev" else None,
    redoc_url="/redoc" if settings.ENV == "dev" else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())[:8]
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s %s status=%d duration=%.1fms",
        req_id,
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    response.headers["X-Request-ID"] = req_id
    return response


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


app.include_router(api_router, prefix="/api/v1")
