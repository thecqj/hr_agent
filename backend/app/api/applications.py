from typing import Optional, Any, Dict

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_required_user
from app.database import get_db
from app.models.user import User
from app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatusUpdateRequest,
)
from app.services import application_service

router = APIRouter(prefix="/applications", tags=["投递"])


_UNSET = object()


def _app_to_dict(app: Any, applicant_name: Optional[str] = None, job_title: Optional[str] = None) -> Dict[str, Any]:
    loaded_applicant = getattr(app, "__dict__", {}).get("applicant", _UNSET)
    resolved_applicant_name = applicant_name
    if resolved_applicant_name is None and loaded_applicant is not _UNSET:
        resolved_applicant_name = loaded_applicant.name if loaded_applicant else None

    return {
        "id": str(app.id),
        "job_id": str(app.job_id),
        "applicant_id": str(app.applicant_id),
        "applicant_name": resolved_applicant_name,
        "job_title": job_title,
        "resume_text": app.resume_text,
        "cover_letter": app.cover_letter,
        "structured_resume": app.structured_resume,
        "status": app.status.value if hasattr(app.status, "value") else app.status,
        "created_at": app.created_at,
    }


@router.post("/", response_model=ApplicationResponse, summary="投递简历", status_code=201)
async def apply(
    data: ApplicationCreateRequest,
    force: bool = Query(False, description="是否覆盖已有投递"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ApplicationResponse:
    application = await application_service.create_application(db, data, current_user, force=force)
    return ApplicationResponse.model_validate(_app_to_dict(application, applicant_name=current_user.name))


@router.get("/my", response_model=ApplicationListResponse, summary="我的投递记录")
async def my_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ApplicationListResponse:
    applications, total = await application_service.get_my_applications(
        db, current_user, page=page, page_size=page_size
    )
    items = [ApplicationResponse.model_validate(_app_to_dict(app, applicant_name=current_user.name)) for app in applications]
    return ApplicationListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/job/{job_id}", response_model=ApplicationListResponse, summary="查看岗位投递列表")
async def job_applications(
    job_id: str = Path(...),
    status: Optional[str] = Query(None, description="状态过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ApplicationListResponse:
    applications, total = await application_service.get_applications_for_job(
        db, job_id, current_user, status_filter=status, page=page, page_size=page_size
    )
    items = [ApplicationResponse.model_validate(_app_to_dict(app)) for app in applications]
    return ApplicationListResponse(total=total, page=page, page_size=page_size, items=items)


@router.patch("/{application_id}/status", response_model=ApplicationResponse, summary="更新申请状态")
async def update_status(
    application_id: str = Path(...),
    data: Optional[ApplicationStatusUpdateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ApplicationResponse:
    if data is None:
        raise ValueError("Application status update data is required")
    application = await application_service.update_application_status(db, application_id, data, current_user)
    return ApplicationResponse.model_validate(_app_to_dict(application))
