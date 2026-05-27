from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from fastapi import HTTPException, status
from app.models.job import Job, WorkType, JobStatus
from app.models.user import User
from app.schemas.job import JobCreateRequest, JobUpdateRequest, JobStatusUpdateRequest
from app.models.user import User, UserRole
from app.models.application import Application

async def create_job(db: AsyncSession, data: JobCreateRequest, current_user: User) -> Job:
    """创建岗位（仅招聘者）"""
    if current_user.role.value != "recruiter":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅招聘者可以发布岗位"
        )
    
    job = Job(
        recruiter_id=current_user.id,
        title=data.title,
        description=data.description,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        location=data.location,
        work_type=data.work_type,
        skills_required=data.skills_required,
        status=JobStatus.ACTIVE,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: str) -> Job:
    """获取单个岗位"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="岗位不存在"
        )
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
    current_user: User = None,
) -> Tuple[list, int]:
    """
    岗位列表（支持过滤、搜索、分页）
    求职者只能看到 active 状态的，招聘者看自己的可加状态过滤
    """
    query = select(Job)
    
    # 搜索关键词：标题或描述
    if keyword:
        query = query.where(
            or_(
                Job.title.ilike(f"%{keyword}%"),
                Job.description.ilike(f"%{keyword}%")
            )
        )
    
    # 地点过滤
    if location:
        query = query.where(Job.location == location)
    
    # 工作类型过滤
    if work_type:
        try:
            wt = WorkType(work_type)
            query = query.where(Job.work_type == wt)
        except ValueError:
            pass
    
    # 薪资范围过滤
    if salary_min is not None:
        query = query.where(Job.salary_max >= salary_min)
    if salary_max is not None:
        query = query.where(Job.salary_min <= salary_max)
    # 用户id过滤    
    if current_user and current_user.role == UserRole.RECRUITER:
        query = query.where(Job.recruiter_id == current_user.id)
    # 状态过滤（可选）
    if status:
        try:
            st = JobStatus(status)
            query = query.where(Job.status == st)
        except ValueError:
            pass
    else:
        # 默认只显示活跃岗位
        query = query.where(Job.status == JobStatus.ACTIVE)
    
    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar()
    
    # 分页
    offset = (page - 1) * page_size
    query = query.order_by(Job.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    for job in jobs:
        count_stmt = select(func.count()).select_from(Application).where(Application.job_id == job.id)
        result = await db.execute(count_stmt)
        job.applications_count = result.scalar()

    return jobs, total


async def update_job(db: AsyncSession, job_id: str, data: JobUpdateRequest, current_user: User) -> Job:
    """更新岗位（仅发布者本人）"""
    job = await get_job(db, job_id)
    
    if job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能编辑自己发布的岗位"
        )
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)
    
    await db.commit()
    await db.refresh(job)
    return job


async def delete_job(db: AsyncSession, job_id: str, current_user: User) -> None:
    # 1. 查找岗位（如果不存在，get_job 会抛出 404）
    job = await get_job(db, job_id)
    
    # 2. 权限检查：仅允许发布者本人删除
    if job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能删除自己发布的岗位"
        )
    
    # 3. 如果岗位有投递记录，需要先删除关联的申请
    from app.models.application import Application
    app_result = await db.execute(
        select(Application).where(Application.job_id == job_id)
    )
    applications = app_result.scalars().all()
    for app in applications:
        await db.delete(app)
    
    # 4. 删除岗位本身（关键！）
    await db.delete(job)
    
    # 5. 提交事务（关键！）
    await db.commit()



async def update_job_status(db: AsyncSession, job_id: str, data: JobStatusUpdateRequest, current_user: User) -> Job:
    """修改岗位状态（仅发布者本人）"""
    job = await get_job(db, job_id)
    
    if job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能修改自己发布的岗位状态"
        )
    
    job.status = data.status
    await db.commit()
    await db.refresh(job)
    return job