from fastapi import APIRouter
from app.api import auth, jobs, applications, agent, chat

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(agent.router)
api_router.include_router(chat.router)
