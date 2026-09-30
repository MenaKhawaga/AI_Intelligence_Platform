from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.logging import setup_logging
from app.core.config import settings
from app.scheduler.jobs import start_scheduler, stop_scheduler

from app.api.routes import (
    admin,
    analytics,
    auth,
    chat,
    intelligence,
    knowledge,
    rag,
    repositories,
    research,
    system,
    trends,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description=(
            "AI Intelligence Platform with an autonomous "
            "tool-calling agent"
        ),
        lifespan=lifespan,
    )

    # ---------------------------------------------------------
    # CORS
    # ---------------------------------------------------------
    origins = [
        x.strip()
        for x in settings.CORS_ALLOW_ORIGINS.split(",")
        if x.strip()
    ]

    if origins == ["*"]:
        origins = [
            "http://127.0.0.1:5500",
            "http://localhost:5500",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------
    # API ROUTES
    # ---------------------------------------------------------
    for router in (
        system.router,
        auth.router,
        chat.router,
        intelligence.router,
        trends.router,
        research.router,
        repositories.router,
        rag.router,
        knowledge.router,
        analytics.router,
        admin.router,
    ):
        app.include_router(router)

    # ---------------------------------------------------------
    # FRONTEND
    # ---------------------------------------------------------
    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"

    if frontend_dir.exists():

        # Admin frontend
        admin_frontend_dir = frontend_dir / "admin"

        if admin_frontend_dir.exists():
            app.mount(
                "/admin",
                StaticFiles(
                    directory=admin_frontend_dir,
                    html=True,
                ),
                name="admin_frontend",
            )

        # User frontend
        app.mount(
            "/",
            StaticFiles(
                directory=frontend_dir,
                html=True,
            ),
            name="frontend",
        )

    return app


app = create_app()