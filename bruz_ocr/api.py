"""Local HTTP application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bruz_ocr import __version__
from bruz_ocr.config import Settings
from bruz_ocr.database import database_is_ready, initialize_database


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        initialize_database(settings.database_path)
        yield

    app = FastAPI(title="Bruz OCR", version=__version__, lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok" if database_is_ready(settings.database_path) else "degraded",
            "version": __version__,
            "mode": "local",
        }

    return app


app = create_app()
