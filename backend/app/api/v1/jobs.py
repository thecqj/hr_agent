from typing import Optional
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.job import (
    JobCreateRequest,
    JobUpdateRequest,
    JobStatusUpdateRequest,
    JobResponse,
    JobListResponse,
)
from app.services import job_service
from app.api.deps import get_required_user, get_optional_user, require_role
from app.models.user import User
from sqlalchemy import func, select
from app.models.application import Application

router = APIRouter(prefix="/jobs", tags=["岗位"])


def _job_to_dict(job, recruiter_name: Optional[str] = None) -> dict:
    """将 ORM 的 Job 对象转换为字典，自动将 UUID 转为字符串"""
    return {
        "id": str(job.id),
        "recruiter_id": str(job.recruiter_id),
        "title": job.title,
        "description": job.description,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "location": job.location,
        "work_type": job.work_type,
        "skills_required": job.skills_required,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "recruiter_name": recruiter_name,
        "applications_count": getattr(job, "applications_count", 0),
    }


@router.post("/", response_model=JobResponse, summary="创建岗位", status_code=201)
async def create_job(
    data: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """创建新岗位（仅招聘者）"""
    job = await job_service.create_job(db, data, current_user)
    # 手动转换 UUID → str
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
    

):
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
    )        # 添加投递数统计
    for job in jobs:
        stmt = select(func.count()).select_from(Application).where(Application.job_id == job.id)
        result = await db.execute(stmt)
        count = result.scalar()
    
    # 构造 items 时，applications_count 会被序列化
        
    """
    岗位列表，公开访问。
    可通过 keyword 搜索标题和描述，支持按地点、工作类型、薪资范围过滤。
    默认只显示活跃岗位。
    """

    
    items = [_job_to_dict(job) for job in jobs]
    
    return JobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/{job_id}", response_model=JobResponse, summary="岗位详情")
async def get_job(
    job_id: str = Path(..., description="岗位ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取岗位详情"""
    job = await job_service.get_job(db, job_id)
    # 这里 recruiter_name 暂时不提供（可关联查询，当前留空）
    return JobResponse.model_validate(_job_to_dict(job))


@router.put("/{job_id}", response_model=JobResponse, summary="更新岗位")
async def update_job(
    job_id: str = Path(..., description="岗位ID"),
    data: JobUpdateRequest = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """更新岗位（仅发布者本人）"""
    job = await job_service.update_job(db, job_id, data, current_user)
    return JobResponse.model_validate(_job_to_dict(job, current_user.name))


@router.delete("/{job_id}", summary="删除岗位")
async def delete_job(
    job_id: str = Path(..., description="岗位ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """删除岗位（仅发布者本人）"""
    await job_service.delete_job(db, job_id, current_user)
    return {"message": "岗位已删除"}


@router.patch("/{job_id}/status", response_model=JobResponse, summary="修改岗位状态")
async def update_job_status(
    job_id: str = Path(..., description="岗位ID"),
    data: JobStatusUpdateRequest = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """修改岗位状态（仅发布者本人）"""
    job = await job_service.update_job_status(db, job_id, data, current_user)
    return JobResponse.model_validate(_job_to_dict(job, current_user.name))