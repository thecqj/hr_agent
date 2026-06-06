from fastapi import APIRouter

from app.api.v1 import applications, auth, jobs, resume_parser, agent

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(agent.router)
api_router.include_router(resume_parser.router)
