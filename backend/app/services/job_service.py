from typing import Optional, Tuple, Sequence, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.models.job import Job, JobStatus, WorkType
from app.models.user import User, UserRole
from app.schemas.job import JobCreateRequest, JobStatusUpdateRequest, JobUpdateRequest


async def create_job(db: AsyncSession, data: JobCreateRequest, current_user: User) -> Job:
    """创建岗位（仅招聘者）"""
    if current_user.role != UserRole.RECRUITER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅招聘者可以发布岗位",
        )

    job = Job(
        recruiter_id=current_user.id,
        title=data.title,
        description=data.description,
        requirements=data.requirements,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        location=data.location,
        work_type=data.work_type,
        skills_required=data.skills_required,
        interview_quota=data.interview_quota,
        status=JobStatus.ACTIVE,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job, attribute_names=["applications"])
    return job


async def get_job(db: AsyncSession, job_id: str) -> Job:
    """获取单个岗位"""
    result = await db.execute(select(Job).where(Job.id == job_id).options(selectinload(Job.applications)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    return job


async def list_jobs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    work_type: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    status: Optional[str] = None,
    current_user: Optional[User] = None,
) -> Tuple[list[Job], int]:
    """岗位列表（支持过滤、搜索、分页）"""
    query = select(Job).options(selectinload(Job.applications))

    if keyword:
        query = query.where(
            or_(
                Job.title.ilike(f"%{keyword}%"),
                Job.description.ilike(f"%{keyword}%"),
            )
        )

    if location:
        query = query.where(Job.location == location)

    if work_type:
        try:
            query = query.where(Job.work_type == WorkType(work_type))
        except ValueError:
            pass

    if salary_min is not None:
        query = query.where(Job.salary_max >= salary_min)
    if salary_max is not None:
        query = query.where(Job.salary_min <= salary_max)

    if current_user and current_user.role == UserRole.RECRUITER:
        query = query.where(Job.recruiter_id == current_user.id)

    if status:
        try:
            query = query.where(Job.status == JobStatus(status))
        except ValueError:
            pass
    else:
        query = query.where(Job.status == JobStatus.ACTIVE)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    page_query = query.order_by(Job.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(page_query)
    jobs = list(result.scalars().all())

    return jobs, total


async def update_job(db: AsyncSession, job_id: str, data: JobUpdateRequest, current_user: User) -> Job:
    """更新岗位（仅发布者本人）"""
    job = await get_job(db, job_id)
    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能编辑自己发布的岗位")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)

    await db.commit()
    await db.refresh(job, attribute_names=["applications"])
    return job


async def delete_job(db: AsyncSession, job_id: str, current_user: User) -> None:
    """删除岗位（仅发布者本人）"""
    job = await get_job(db, job_id)
    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能删除自己发布的岗位")

    app_result = await db.execute(select(Application).where(Application.job_id == job_id))
    for application in app_result.scalars().all():
        await db.delete(application)

    await db.delete(job)
    await db.commit()


async def update_job_status(
    db: AsyncSession,
    job_id: str,
    data: JobStatusUpdateRequest,
    current_user: User,
) -> Job:
    """修改岗位状态（仅发布者本人）"""
    job = await get_job(db, job_id)
    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能修改自己发布的岗位状态")

    job.status = data.status
    await db.commit()
    await db.refresh(job, attribute_names=["applications"])
    return job
