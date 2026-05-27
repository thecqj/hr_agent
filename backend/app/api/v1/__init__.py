from fastapi import APIRouter
from app.api.v1 import auth, jobs, applications, agent, resume_parser

# 先创建 api_router 实例
api_router = APIRouter(prefix="/api/v1")

# 然后注册各个子路由
api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(agent.router)
api_router.include_router(resume_parser.router)