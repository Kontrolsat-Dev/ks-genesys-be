# apps/api_main.py
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.infra.bootstrap import ensure_recurring_jobs


# Routes
from app.api.v1.auth import router as auth_router
from app.api.v1.audit import router as audit_router
from app.api.v1.feeds import router as feeds_router
from app.api.v1.mappers import router as mappers_router
from app.api.v1.products import router as products_router
from app.api.v1.runs import router as runs_router
from app.api.v1.suppliers import router as suppliers_router
from app.api.v1.brands import router as brands_router
from app.api.v1.categories import router as categories_router
from app.api.v1.catalog_update_stream import router as catalog_updates_router
from app.api.v1.worker_jobs import router as worker_jobs_router
from app.api.v1.prestashop import router as prestashop_router
from app.api.v1.orders_dropshipping import router as dropshipping_router
from app.api.v1.config import router as config_router
from app.api.v1.system import router as system_router

# Others
from app.core.http_errors import init_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.config import settings

setup_logging()


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.add_middleware(RequestContextMiddleware)

init_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",  # aceita qualquer origem
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,  # ecoa o Origin em vez de '*'
    max_age=86400,
)


@app.on_event("startup")
async def on_startup():
    app.state.started_at = datetime.now(UTC)
    from app.models import create_db_and_tables
    from app.infra.session import SessionLocal

    create_db_and_tables()
    ensure_recurring_jobs(SessionLocal)


# routers
app.include_router(system_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(prestashop_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(suppliers_router, prefix="/api/v1")
app.include_router(feeds_router, prefix="/api/v1")
app.include_router(mappers_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(brands_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(catalog_updates_router, prefix="/api/v1")
app.include_router(worker_jobs_router, prefix="/api/v1")
app.include_router(dropshipping_router, prefix="/api/v1")
