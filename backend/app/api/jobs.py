from typing import Optional, Any, Dict

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user, get_required_user
from app.database import get_db
from app.models.user import User
from app.schemas.job import (
    JobCreateRequest,
    JobListResponse,
    JobResponse,
    JobStatusUpdateRequest,
    JobUpdateRequest,
)
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["岗位"])


def _job_to_dict(job: Any, recruiter_name: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": str(job.id),
        "recruiter_id": str(job.recruiter_id),
        "title": job.title,
        "description": job.description,
        "requirements": job.requirements,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "location": job.location,
        "work_type": job.work_type,
        "skills_required": job.skills_required,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "recruiter_name": recruiter_name,
        "applications_count": len(job.applications),
        "head_count": job.head_count,
        "job_code": job.job_code,
    }


@router.post("/", response_model=JobResponse, summary="创建岗位", status_code=201)
async def create_job(
    data: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> JobResponse:
    job = await job_service.create_job(db, data, current_user)
    return JobResponse.model_validate(_job_to_dict(job, current_user.name))


@router.get("/", response_model=JobListResponse, summary="岗位列表")
async def list_jobs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    location: Optional[str] = Query(None, description="工作地点"),
    work_type: Optional[str] = Query(None, description="工作类型：remote/onsite/hybrid"),
    salary_min: Optional[int] = Query(None, description="最低薪资过滤"),
    salary_max: Optional[int] = Query(None, description="最高薪资过滤"),
    status: Optional[str] = Query(None, description="岗位状态过滤（招聘者可用）"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    jobs, total = await job_service.list_jobs(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        location=location,
        work_type=work_type,
        salary_min=salary_min,
        salary_max=salary_max,
        status=status,
        current_user=current_user,
    )

    return JobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[JobResponse.model_validate(_job_to_dict(job)) for job in jobs],
    )


@router.get("/{job_id}", response_model=JobResponse, summary="岗位详情")
async def get_job(
    job_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    job = await job_service.get_job(db, job_id)
    return JobResponse.model_validate(_job_to_dict(job))


@router.put("/{job_id}", response_model=JobResponse, summary="更新岗位")
async def update_job(
    job_id: str = Path(...),
    data: Optional[JobUpdateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> JobResponse:
    if data is None:
        raise ValueError("Job update data is required")
    job = await job_service.update_job(db, job_id, data, current_user)
    return JobResponse.model_validate(_job_to_dict(job, current_user.name))


@router.delete("/{job_id}", summary="删除岗位")
async def delete_job(
    job_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> Dict[str, str]:
    await job_service.delete_job(db, job_id, current_user)
    return {"message": "岗位已删除"}


@router.patch("/{job_id}/status", response_model=JobResponse, summary="修改岗位状态")
async def update_job_status(
    job_id: str = Path(...),
    data: Optional[JobStatusUpdateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> JobResponse:
    if data is None:
        raise ValueError("Job status update data is required")
    job = await job_service.update_job_status(db, job_id, data, current_user)
    return JobResponse.model_validate(_job_to_dict(job, current_user.name))
