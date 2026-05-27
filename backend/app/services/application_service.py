from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from app.models.user import User
from app.schemas.application import ApplicationCreateRequest, ApplicationStatusUpdateRequest
from typing import List, Optional
from sqlalchemy.orm import selectinload

async def create_application(
    db: AsyncSession,
    data: ApplicationCreateRequest,
    current_user: User,
    force: bool = False
) -> Application:
    """求职者投递岗位"""
    # 1. 检查角色
    if current_user.role.value != "job_seeker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅求职者可以投递简历"
        )

    # 2. 检查岗位是否存在且为活跃状态
    job = await db.get(Job, data.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    if job.status.value != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="岗位已关闭，无法投递")

    # 3. 检查是否已投递过
    existing = await db.execute(
        select(Application).where(
            Application.job_id == data.job_id,
            Application.applicant_id == current_user.id
        )
    )
    existing_app = existing.scalar_one_or_none()

    if existing_app:
        if force:
            # 覆盖原有申请
            existing_app.resume_text = data.resume_text
            existing_app.cover_letter = data.cover_letter
            existing_app.structured_resume = data.structured_resume.model_dump() if data.structured_resume else None
            existing_app.status = ApplicationStatus.PENDING
            existing_app.match_score = None
            existing_app.ai_suggestions = None
            await db.commit()
            await db.refresh(existing_app)
            return existing_app
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="您已投递过该岗位，是否覆盖原简历？"
            )

    # 4. 创建新申请
    application = Application(
        job_id=data.job_id,
        applicant_id=current_user.id,
        resume_text=data.resume_text,
        cover_letter=data.cover_letter,
        structured_resume=data.structured_resume.model_dump() if data.structured_resume else None,
        match_score=None,
        ai_suggestions=None,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


async def get_applications_for_job(
    db: AsyncSession,
    job_id: str,
    current_user: User,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> tuple[List[Application], int]:
    """招聘者查看某个岗位的投递列表"""
    # 1. 验证岗位所有权
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此岗位的投递")

    # 2. 构建查询
    query = select(Application).where(Application.job_id == job_id)
    query = query.options(selectinload(Application.applicant))
    if status_filter:
        try:
            st = ApplicationStatus(status_filter)
            query = query.where(Application.status == st)
        except ValueError:
            pass

    # 3. 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # 4. 分页
    offset = (page - 1) * page_size
    query = query.order_by(Application.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    applications = result.scalars().all()

    return applications, total


async def get_my_applications(
    db: AsyncSession,
    current_user: User,
    page: int = 1,
    page_size: int = 20
) -> tuple[List[Application], int]:
    """求职者查看自己的投递记录"""
    query = select(Application).where(Application.applicant_id == current_user.id)
    query = query.options(selectinload(Application.applicant))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    offset = (page - 1) * page_size
    query = query.order_by(Application.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    applications = result.scalars().all()

    return applications, total


async def update_application_status(
    db: AsyncSession,
    application_id: str,
    data: ApplicationStatusUpdateRequest,
    current_user: User
) -> Application:
    """招聘者更新申请状态"""
    application = await db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申请不存在")

    # 验证岗位所有权
    job = await db.get(Job, application.job_id)
    if not job or job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此申请")

    application.status = data.status
    await db.commit()
    await db.refresh(application)
    return application