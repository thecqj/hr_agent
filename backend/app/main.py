from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 统一挂载 /api 路由
app.include_router(api_router)


@app.get("/", response_model=Dict[str, Any])
async def root() -> Dict[str, Any]:
    return {
        "message": f"{settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}
