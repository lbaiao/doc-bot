from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import engine
from app.routers import admin, auth, chats, documents, search, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    setup_logging()
    
    # TODO: Initialize vector DB connection
    # TODO: Initialize Redis connection for Celery
    
    yield
    
    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health checks (no prefix)
    app.include_router(admin.router)
    
    # API v1 routes
    api_v1_prefix = "/v1"
    
    app.include_router(auth.router, prefix=f"{api_v1_prefix}/auth")
    app.include_router(users.router, prefix=api_v1_prefix)
    app.include_router(documents.router, prefix=api_v1_prefix)
    app.include_router(chats.router, prefix=api_v1_prefix)
    app.include_router(search.router, prefix=api_v1_prefix)
    
    return app


app = create_app()
