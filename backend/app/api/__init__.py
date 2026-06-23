from fastapi import APIRouter
from app.api import auth, jobs, applications

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
