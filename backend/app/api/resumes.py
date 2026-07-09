from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_required_user
from app.database import get_db
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import (
    ParseResumeResponse,
    ResumeCreateRequest,
    ResumeListItem,
    ResumeListResponse,
    ResumeResponse,
    ResumeUpdateFullRequest,
    ResumeUpdateRequest,
)
from app.schemas.application import StructuredResume
from app.services.resume_service import parse_resume_file

router = APIRouter(prefix="/resumes", tags=["简历"])


@router.post("/parse", response_model=ParseResumeResponse, summary="上传并解析简历（不保存）")
async def parse_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ParseResumeResponse:
    """上传简历文件并解析为结构化数据，不保存到简历库。用于投递页面自动填充表单。"""
    _, parsed_text, structured_data = await parse_resume_file(file)
    return ParseResumeResponse(
        parsed_text=parsed_text,
        structured_data=StructuredResume.model_validate(structured_data),
    )


@router.post("/", response_model=ResumeResponse, summary="上传并保存简历", status_code=201)
async def create_resume(
    file: UploadFile = File(...),
    name: str = Form(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ResumeResponse:
    """上传简历文件，解析并保存到用户的简历库。"""
    file_bytes, parsed_text, structured_data = await parse_resume_file(file)
    resume = Resume(
        user_id=current_user.id,
        name=name,
        file_name=file.filename or "resume",
        file_type=file.content_type or "application/octet-stream",
        file_data=file_bytes,
        parsed_text=parsed_text,
        structured_data=structured_data,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return ResumeResponse.model_validate(resume)


@router.get("/", response_model=ResumeListResponse, summary="获取简历列表")
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ResumeListResponse:
    """获取当前用户的简历列表（不含文件数据和结构化数据）。"""
    stmt = (
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
    )
    result = await db.execute(stmt)
    resumes = list(result.scalars().all())

    count_stmt = select(func.count()).select_from(Resume).where(Resume.user_id == current_user.id)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    items = [ResumeListItem.model_validate(r) for r in resumes]
    return ResumeListResponse(total=total, items=items)


@router.get("/{resume_id}", response_model=ResumeResponse, summary="获取简历详情")
async def get_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ResumeResponse:
    """获取单份简历详情（含结构化数据）。"""
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简历不存在")
    if resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此简历")

    return ResumeResponse.model_validate(resume)


@router.get("/{resume_id}/download", summary="下载简历文件")
async def download_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, Any]:
    """下载简历文件（返回文件数据的 Base64 编码）。"""
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简历不存在")
    if resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此简历")

    import base64
    assert resume.file_data is not None
    file_data_b64 = base64.b64encode(resume.file_data).decode("utf-8")

    return {
        "file_name": resume.file_name,
        "file_type": resume.file_type,
        "file_data": file_data_b64,
    }


@router.put("/{resume_id}", response_model=ResumeResponse, summary="更新简历信息")
async def update_resume(
    resume_id: str,
    data: ResumeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ResumeResponse:
    """更新简历名称。"""
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简历不存在")
    if resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此简历")

    resume.name = data.name
    await db.commit()
    await db.refresh(resume)
    return ResumeResponse.model_validate(resume)


@router.put("/{resume_id}/data", response_model=ResumeResponse, summary="更新简历完整信息（含结构化数据）")
async def update_resume_data(
    resume_id: str,
    data: ResumeUpdateFullRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ResumeResponse:
    """更新简历的完整信息，包括结构化数据和解析文本。"""
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简历不存在")
    if resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此简历")

    resume.name = data.name
    if data.parsed_text is not None:
        resume.parsed_text = data.parsed_text
    if data.structured_data is not None:
        resume.structured_data = data.structured_data
    await db.commit()
    await db.refresh(resume)
    return ResumeResponse.model_validate(resume)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除简历")
async def delete_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> None:
    """删除简历。"""
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简历不存在")
    if resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除此简历")

    await db.delete(resume)
    await db.commit()