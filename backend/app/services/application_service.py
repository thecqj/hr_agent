from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from app.models.user import User, UserRole
from app.schemas.application import ApplicationCreateRequest, ApplicationStatusUpdateRequest


async def create_application(
    db: AsyncSession,
    data: ApplicationCreateRequest,
    current_user: User,
    force: bool = False,
) -> Application:
    """求职者投递岗位"""
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅求职者可以投递简历")

    job = await db.get(Job, data.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    if job.status.value != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="岗位已关闭，无法投递")

    existing_stmt = select(Application).where(
        Application.job_id == data.job_id,
        Application.applicant_id == current_user.id,
    )
    existing_app = (await db.execute(existing_stmt)).scalar_one_or_none()

    if existing_app:
        if existing_app.status == ApplicationStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="该岗位已拒绝您的投递，无法再次申请",
            )
        if not force:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="您已投递过该岗位，是否覆盖原简历？",
            )

        existing_app.resume_text = data.resume_text
        existing_app.cover_letter = data.cover_letter
        existing_app.structured_resume = data.structured_resume.model_dump() if data.structured_resume else None
        existing_app.status = ApplicationStatus.PENDING
        await db.commit()
        await db.refresh(existing_app, attribute_names=["job"])
        return existing_app

    application = Application(
        job_id=data.job_id,
        applicant_id=current_user.id,
        resume_text=data.resume_text,
        cover_letter=data.cover_letter,
        structured_resume=data.structured_resume.model_dump() if data.structured_resume else None,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application, attribute_names=["job"])
    return application


async def get_applications_for_job(
    db: AsyncSession,
    job_id: str,
    current_user: User,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[list[Application], int]:
    """招聘者查看某个岗位的投递列表"""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此岗位的投递")

    query = select(Application).where(Application.job_id == job_id).options(selectinload(Application.applicant))

    if status_filter:
        try:
            query = query.where(Application.status == ApplicationStatus(status_filter))
        except ValueError:
            pass

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    page_query = query.order_by(Application.created_at.desc()).offset(offset).limit(page_size)
    applications = list((await db.execute(page_query)).scalars().all())
    return applications, total


async def get_my_applications(
    db: AsyncSession,
    current_user: User,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[list[Application], int]:
    """求职者查看自己的投递记录"""
    query = select(Application).where(Application.applicant_id == current_user.id).options(
        selectinload(Application.applicant),
        selectinload(Application.job),
    )

    if status_filter:
        try:
            query = query.where(Application.status == ApplicationStatus(status_filter))
        except ValueError:
            pass

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    page_query = query.order_by(Application.created_at.desc()).offset(offset).limit(page_size)
    applications = list((await db.execute(page_query)).scalars().all())
    return applications, total


async def update_application_status(
    db: AsyncSession,
    application_id: str,
    data: ApplicationStatusUpdateRequest,
    current_user: User,
) -> Application:
    """招聘者更新申请状态"""
    application = await db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申请不存在")

    job = await db.get(Job, application.job_id)
    if not job or job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此申请")

    application.status = data.status
    await db.commit()
    await db.refresh(application)
    return application


async def count_by_job_and_status(
    db: AsyncSession,
    job_id: str,
    status: str,
) -> int:
    """统计某岗位指定状态的申请数量"""
    try:
        app_status = ApplicationStatus(status)
    except ValueError:
        return 0

    stmt = select(func.count()).select_from(Application).where(
        Application.job_id == job_id,
        Application.status == app_status,
    )
    result = (await db.execute(stmt)).scalar()
    return result or 0


async def count_by_job_grouped_by_status(
    db: AsyncSession,
    job_id: str,
) -> dict[str, int]:
    """按状态分组统计某岗位的申请数量

    返回所有 ApplicationStatus 枚举值作为 key，计数为 0 的状态也包含在内，
    确保下游消费者始终拿到完整的状态字典。
    """
    result: dict[str, int] = {s.value: 0 for s in ApplicationStatus}
    stmt = (
        select(Application.status, func.count())
        .where(Application.job_id == job_id)
        .group_by(Application.status)
    )
    rows = (await db.execute(stmt)).all()
    result.update({row[0].value: row[1] for row in rows})
    return result


async def list_by_job(
    db: AsyncSession,
    job_id: str,
    decision_filter: str | None = None,
) -> list[Application]:
    """列出某岗位的申请，可选按 AI decision 过滤"""
    stmt = (
        select(Application)
        .where(Application.job_id == job_id)
        .options(selectinload(Application.applicant))
    )

    if decision_filter:
        stmt = stmt.where(Application.ai_decision == decision_filter)

    stmt = stmt.order_by(Application.ai_score.desc().nullslast(), Application.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
