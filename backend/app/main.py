
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.auth import router as auth_router
from app.api.v1.accounts import router as accounts_router
from app.api.v1.transactions import router as transactions_router
from app.core.config import settings
from app.db.session import get_db


app = FastAPI(
    title=settings.app_name,
    description="LedgerLine - Secure and auditable financial transaction system",
    version="1.0.0",
    debug=settings.debug,
)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Idempotency-Key",
    ],
)


# Register API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(accounts_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")


@app.get("/", tags=["General"])
def root():
    return {
        "message": "Welcome to LedgerLine API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "unavailable",
            },
        )
