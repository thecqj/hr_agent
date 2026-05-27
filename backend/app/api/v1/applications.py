from typing import Optional
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationListResponse,
    ApplicationStatusUpdateRequest,
)
from app.services import application_service
from app.api.deps import get_required_user, get_optional_user
from app.models.user import User
from fastapi import BackgroundTasks
router = APIRouter(prefix="/applications", tags=["投递"])

def _app_to_dict(app, applicant_name=None, job_title=None):
    return {
        "id": str(app.id),
        "job_id": str(app.job_id),
        "applicant_id": str(app.applicant_id),
        "applicant_name": applicant_name or (app.applicant.name if app.applicant else None),
        "job_title": job_title,
        "resume_text": app.resume_text,
        "cover_letter": app.cover_letter,
        "match_score": app.match_score,
        "ai_suggestions": app.ai_suggestions,
        "structured_resume": app.structured_resume,
        "status": app.status.value if hasattr(app.status, 'value') else app.status,
        "created_at": app.created_at.isoformat() if app.created_at else None,
    }


@router.post("/", response_model=ApplicationResponse, summary="投递简历", status_code=201)
async def apply(
    data: ApplicationCreateRequest,
    force: bool = Query(False, description="是否覆盖已有投递"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    application = await application_service.create_application(db, data, current_user, force=force)
    return ApplicationResponse.model_validate(_app_to_dict(application, applicant_name=current_user.name))

@router.get("/my", response_model=ApplicationListResponse, summary="我的投递记录")
async def my_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """求职者查看自己的投递记录"""
    applications, total = await application_service.get_my_applications(
        db, current_user, page=page, page_size=page_size
    )
    items = [_app_to_dict(a, applicant_name=current_user.name) for a in applications]
    return ApplicationListResponse(total=total, items=items)


@router.get("/job/{job_id}", response_model=ApplicationListResponse, summary="查看岗位投递列表")
async def job_applications(
    job_id: str = Path(..., description="岗位ID"),
    status: Optional[str] = Query(None, description="状态过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """招聘者查看自己岗位的投递列表"""
    applications, total = await application_service.get_applications_for_job(
        db, job_id, current_user, status_filter=status, page=page, page_size=page_size
    )
    # 这里简单处理，未从关联查询获取姓名和岗位标题，如需要可扩展
    items = [_app_to_dict(a) for a in applications]
    return ApplicationListResponse(total=total, items=items)


@router.patch("/{application_id}/status", response_model=ApplicationResponse, summary="更新申请状态")
async def update_status(
    application_id: str = Path(..., description="申请ID"),
    data: ApplicationStatusUpdateRequest = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """招聘者更新申请状态"""
    application = await application_service.update_application_status(
        db, application_id, data, current_user
    )
    return ApplicationResponse.model_validate(_app_to_dict(application))

@router.get("/my", response_model=ApplicationListResponse, summary="我的投递记录")
async def my_applications():
    applications, total = await application_service.get_my_applications(...)
    items = []
    for app in applications:
        app_dict = _app_to_dict(app)
        # 补充岗位标题和公司名
        job = await db.get(Job, app.job_id)
        if job:
            app_dict["job_title"] = job.title
            # 查询招聘者公司
            recruiter = await db.get(User, job.recruiter_id)
            recruiter_profile = await db.get(RecruiterProfile, job.recruiter_id)
            app_dict["company_name"] = recruiter_profile.company_name if recruiter_profile else None
        items.append(app_dict)
    return ApplicationListResponse(total=total, items=items)

@router.post("/", response_model=ApplicationResponse, status_code=201)
async def apply(
    data: ApplicationCreateRequest,
    background_tasks: BackgroundTasks, 
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
    
):
    application = await application_service.create_application(
        db, data, current_user, force=force
    )
    count_stmt = select(func.count()).where(Application.job_id == data.job_id)
    count = (await db.execute(count_stmt)).scalar()
    if count >= 5:
        # 启动后台评估任务
        background_tasks.add_task(
            run_batch_evaluation, str(application.job_id), db
        )
    # 返回时结构化数据
    resp = ApplicationResponse.model_validate(_app_to_dict(application))
    resp.structured_resume = application.structured_resume
    return resp