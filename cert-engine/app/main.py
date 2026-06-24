"""
CAT Engine - FastAPI Application Entry Point.

Computerized Adaptive Testing engine for MuleSoft Agentic Enterprise certification.
Uses SPRT (Sequential Probability Ratio Test) for pass/fail classification
with 2PL IRT-based item selection.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health, exam, items


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="CAT Certification Engine",
        description=(
            "Computerized Adaptive Testing engine for the "
            "MuleSoft Agentic Enterprise certification. "
            "Uses SPRT classification with 2PL IRT item selection."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS (allow admin UI served from same origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health.router)
    app.include_router(exam.router)
    app.include_router(items.router)

    @app.get("/")
    async def root():
        return {
            "service": "CAT Certification Engine",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health/ready",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
