# 简历上传解析与个人中心 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add resume file upload (drag-and-drop + file picker), LLM-based resume parsing to auto-fill application forms, and a user profile center for managing multiple named resumes.

**Architecture:** Backend — new `resumes` DB table + service layer for text extraction (PDF/DOCX/TXT) + DeepSeek LLM integration for structured parsing + CRUD API. Frontend — new `resumes` feature folder with uploader component, profile page, and API client; extend existing SeekerLayout dropdown and App routing.

**Tech Stack:** FastAPI + SQLAlchemy 2.x async + Pydantic v2 + DeepSeek LLM (backend), React 19 + TypeScript + Vite + shadcn/ui + Zustand + TanStack Query (frontend), PyPDF2 + python-docx (PDF/DOCX text extraction).

## Global Constraints

- All new Python code must pass `mypy --strict`
- UUID primary keys, serialized as strings in API responses
- Pydantic v2 `BaseModel` for all API boundaries
- File upload size limit: 10MB
- Supported file types: PDF (`application/pdf`), DOCX (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`), TXT (`text/plain`)
- Chinese-language UI labels and error messages
- Follow existing code patterns: `apiClient` for HTTP, `useMutation`/`useQuery` for data fetching, `react-hook-form` + `zod` for forms

---

### Task 1: Add dependencies (PyPDF2 + python-docx)

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add PyPDF2 and python-docx to requirements.txt**

```
# ... existing content ...
PyPDF2
python-docx
```

Add after the existing `httpx` line.

- [ ] **Step 2: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add PyPDF2 and python-docx for resume text extraction"
```

---

### Task 2: Create Resume ORM model

**Files:**
- Create: `backend/app/models/resume.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/database.py`
- Modify: `backend/alembic/env.py`

- [ ] **Step 1: Create `backend/app/models/resume.py`**

```python
import uuid
from typing import Optional, Any, TYPE_CHECKING

from sqlalchemy import String, Text, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    parsed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_data: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="resumes")

    def __repr__(self) -> str:
        return f"<Resume {self.name} user={self.user_id}>"


if TYPE_CHECKING:
    from app.models.user import User
```

- [ ] **Step 2: Add Resume to `backend/app/models/__init__.py`**

Add import and export:
```python
from app.models.resume import Resume

__all__ = [
    # ... existing entries ...
    "Resume",
]
```

- [ ] **Step 3: Add import to `backend/app/database.py`**

Add after the existing model imports:
```python
import app.models.resume  # noqa: F401
```

- [ ] **Step 4: Add import to `backend/alembic/env.py`**

Add after the existing model imports:
```python
import app.models.resume  # noqa: F401
```

- [ ] **Step 5: Add `resumes` relationship to User model (`backend/app/models/user.py`)**

After the existing `applications` relationship:
```python
resumes: Mapped[list["Resume"]] = relationship(
    "Resume",
    back_populates="user",
    cascade="all, delete-orphan",
)
```

And add `Resume` to the TYPE_CHECKING import block.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/resume.py backend/app/models/__init__.py backend/app/database.py backend/alembic/env.py backend/app/models/user.py
git commit -m "feat: add Resume ORM model and relationships"
```

---

### Task 3: Create Alembic migration for resumes table

**Files:**
- Create: new migration file in `backend/alembic/versions/`

- [ ] **Step 1: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add resumes table"
```

- [ ] **Step 2: Verify the generated migration creates the resumes table correctly**

If autogenerate didn't detect it, write the migration manually:

```python
"""add resumes table

Revision ID: xxxx
Revises: <previous>
Create Date: 2026-07-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

revision: str = "xxxx"
down_revision: Union[str, None] = "<previous>"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("resumes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_data", sa.LargeBinary, nullable=False),
        sa.Column("parsed_text", sa.Text, nullable=True),
        sa.Column("structured_data", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_resumes_user_id", table_name="resumes")
    op.drop_table("resumes")
```

- [ ] **Step 3: Run migration**

```bash
cd backend
alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add migration for resumes table"
```

---

### Task 4: Create Resume Pydantic schemas

**Files:**
- Create: `backend/app/schemas/resume.py`

- [ ] **Step 1: Create `backend/app/schemas/resume.py`**

```python
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_serializer

from app.schemas.application import StructuredResume


class ResumeListItem(BaseModel):
    """简历列表项（不含文件数据和结构化数据）"""
    id: str
    name: str
    file_name: str
    file_type: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_uuid(self, value: uuid.UUID | str, _info: Any) -> str:
        return str(value)


class ResumeResponse(BaseModel):
    """简历详情响应"""
    id: str
    user_id: str
    name: str
    file_name: str
    file_type: str
    parsed_text: Optional[str] = None
    structured_data: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "user_id")
    def serialize_uuid(self, value: uuid.UUID | str, _info: Any) -> str:
        return str(value)


class ResumeListResponse(BaseModel):
    """简历列表响应"""
    total: int
    items: list[ResumeListItem]


class ResumeCreateRequest(BaseModel):
    """创建简历请求（上传保存）"""
    name: str = Field(..., min_length=1, max_length=100, description="简历名称")


class ResumeUpdateRequest(BaseModel):
    """更新简历请求"""
    name: str = Field(..., min_length=1, max_length=100, description="简历名称")


class ParseResumeResponse(BaseModel):
    """简历解析响应（不保存，仅用于填充表单）"""
    parsed_text: str
    structured_data: StructuredResume
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/resume.py
git commit -m "feat: add Resume Pydantic schemas"
```

---

### Task 5: Add `parse_resume` method to LLM base and DeepSeek provider

**Files:**
- Modify: `backend/app/llm/base.py`
- Modify: `backend/app/llm/deepseek.py`

- [ ] **Step 1: Add abstract method to `backend/app/llm/base.py`**

After the `summarize_conversation` method:
```python
@abstractmethod
async def parse_resume(self, raw_text: str) -> dict[str, object]:
    """将简历原始文本解析为结构化数据
    
    Args:
        raw_text: 从简历文件中提取的纯文本
        
    Returns:
        结构化简历数据字典，结构与 StructuredResume 一致
    """
    ...
```

- [ ] **Step 2: Add implementation to `backend/app/llm/deepseek.py`**

Add the method to the `DeepSeekProvider` class:
```python
async def parse_resume(self, raw_text: str) -> dict[str, object]:
    """将简历原始文本解析为结构化数据"""
    system_prompt = """你是一位专业的简历解析助手。请从以下简历文本中提取信息，输出严格的结构化 JSON。

请严格按照以下 JSON Schema 输出，不要输出任何其他内容：
{
  "name": "姓名",
  "work_experience_years": 5,
  "education_level": "本科/硕士/博士等",
  "contact": {
    "phone": "电话",
    "email": "邮箱",
    "wechat": "微信",
    "other": "其他联系方式"
  },
  "work_experience": [
    {
      "company": "公司名",
      "position": "职位",
      "start_date": "开始日期",
      "end_date": "结束日期（或null）",
      "description": "工作描述"
    }
  ],
  "project_experience": [
    {
      "name": "项目名",
      "role": "角色",
      "start_date": "开始日期",
      "end_date": "结束日期（或null）",
      "description": "项目描述",
      "technologies": ["技术栈列表"]
    }
  ],
  "education": [
    {
      "school": "学校名",
      "major": "专业",
      "degree": "学位",
      "start_date": "开始日期",
      "end_date": "结束日期（或null）"
    }
  ],
  "certificates": [
    {
      "name": "证书名称",
      "date": "获得日期（或null）"
    }
  ],
  "skills": ["技能列表"],
  "self_evaluation": "自我评价（或null）"
}

## 规则
- 如果简历中没有某个字段的信息，该字段使用空数组 [] 或 null
- 日期格式保持原文格式即可
- 工作年限根据简历中的工作经历推算
- 确保输出是合法的 JSON 对象"""

    user_prompt = f"请解析以下简历文本：\n\n{raw_text}"

    raw = await self._call_chat(
        system_prompt, user_prompt, retries=settings.LLM_EVALUATION_RETRIES
    )
    return raw
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/llm/base.py backend/app/llm/deepseek.py
git commit -m "feat: add parse_resume method to LLM provider"
```

---

### Task 6: Create resume service (text extraction + LLM parsing)

**Files:**
- Create: `backend/app/services/resume_service.py`

- [ ] **Step 1: Create `backend/app/services/resume_service.py`**

```python
import io
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status

from app.llm.deepseek import DeepSeekProvider

ALLOWED_CONTENT_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}

MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB


async def extract_text_from_pdf(file_stream: BinaryIO) -> str:
    """从 PDF 文件中提取文本"""
    from PyPDF2 import PdfReader

    reader = PdfReader(file_stream)
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


async def extract_text_from_docx(file_stream: BinaryIO) -> str:
    """从 DOCX 文件中提取文本"""
    from docx import Document

    doc = Document(file_stream)
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text.strip())
    return "\n".join(paragraphs)


async def extract_text_from_txt(file_stream: BinaryIO) -> str:
    """从 TXT 文件中提取文本"""
    content = file_stream.read()
    return content.decode("utf-8", errors="replace")


async def extract_text(file_bytes: bytes, content_type: str) -> str:
    """根据文件类型提取文本"""
    file_stream = io.BytesIO(file_bytes)

    if content_type == "application/pdf":
        return await extract_text_from_pdf(file_stream)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return await extract_text_from_docx(file_stream)
    elif content_type == "text/plain":
        return await extract_text_from_txt(file_stream)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {content_type}",
        )


async def parse_resume_file(file: UploadFile) -> tuple[str, dict[str, object]]:
    """上传并解析简历文件，返回 (parsed_text, structured_data)"""
    # 验证文件类型
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {content_type}，仅支持 PDF、DOCX、TXT",
        )

    # 读取文件内容
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件内容为空",
        )
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE // (1024 * 1024)}MB）",
        )

    # 提取文本
    try:
        parsed_text = await extract_text(file_bytes, content_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"文件文本提取失败: {exc}",
        )

    if not parsed_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="无法从文件中提取到有效文本内容",
        )

    # 调用 LLM 解析
    try:
        llm = DeepSeekProvider()
        structured_data = await llm.parse_resume(parsed_text)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"简历解析失败: {exc}",
        )

    return parsed_text, structured_data
```

- [ ] **Step 2: Update `backend/app/services/__init__.py`**

```python
from . import agent_service, application_service, auth_service, job_service, resume_service

__all__ = [
    "agent_service",
    "application_service",
    "auth_service",
    "job_service",
    "resume_service",
]
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/resume_service.py backend/app/services/__init__.py
git commit -m "feat: add resume service with text extraction and LLM parsing"
```

---

### Task 7: Create Resume API routes

**Files:**
- Create: `backend/app/api/resumes.py`
- Modify: `backend/app/api/__init__.py`

- [ ] **Step 1: Create `backend/app/api/resumes.py`**

```python
from typing import Optional

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
    parsed_text, structured_data = await parse_resume_file(file)
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
    parsed_text, structured_data = await parse_resume_file(file)

    file_bytes = await file.read()
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
) -> dict:
    """下载简历文件（返回文件数据的 Base64 编码）。"""
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简历不存在")
    if resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此简历")

    import base64
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
```

- [ ] **Step 2: Register router in `backend/app/api/__init__.py`**

```python
from app.api import auth, jobs, applications, agent, chat, resumes

api_router.include_router(resumes.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/resumes.py backend/app/api/__init__.py
git commit -m "feat: add Resume CRUD and parse API routes"
```

---

### Task 8: Frontend — API client and hooks for resumes

**Files:**
- Create: `frontend/src/features/resumes/api/resumes.ts`
- Create: `frontend/src/features/resumes/hooks/useResumes.ts`
- Modify: `frontend/src/shared/constants/queryKeys.ts`

- [ ] **Step 1: Create `frontend/src/features/resumes/api/resumes.ts`**

```typescript
import { apiClient } from "@/shared/api/client";
import type { StructuredResume } from "@/features/applications/types/application";

export interface ResumeListItem {
  id: string;
  name: string;
  file_name: string;
  file_type: string;
  created_at: string;
}

export interface ResumeResponse {
  id: string;
  user_id: string;
  name: string;
  file_name: string;
  file_type: string;
  parsed_text: string | null;
  structured_data: StructuredResume | null;
  created_at: string;
  updated_at: string;
}

export interface ResumeListResponse {
  total: number;
  items: ResumeListItem[];
}

export interface ParseResumeResponse {
  parsed_text: string;
  structured_data: StructuredResume;
}

export interface DownloadResponse {
  file_name: string;
  file_type: string;
  file_data: string; // base64
}

export async function parseResume(file: File): Promise<ParseResumeResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiClient.post<ParseResumeResponse>("/resumes/parse", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function uploadResume(file: File, name: string): Promise<ResumeResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  const res = await apiClient.post<ResumeResponse>("/resumes/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function getResumeList(): Promise<ResumeListResponse> {
  const res = await apiClient.get<ResumeListResponse>("/resumes/");
  return res.data;
}

export async function getResumeDetail(id: string): Promise<ResumeResponse> {
  const res = await apiClient.get<ResumeResponse>(`/resumes/${id}`);
  return res.data;
}

export async function downloadResume(id: string): Promise<DownloadResponse> {
  const res = await apiClient.get<DownloadResponse>(`/resumes/${id}/download`);
  return res.data;
}

export async function updateResumeName(id: string, name: string): Promise<ResumeResponse> {
  const res = await apiClient.put<ResumeResponse>(`/resumes/${id}`, { name });
  return res.data;
}

export async function deleteResume(id: string): Promise<void> {
  await apiClient.delete(`/resumes/${id}`);
}
```

- [ ] **Step 2: Create `frontend/src/features/resumes/hooks/useResumes.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  deleteResume,
  getResumeDetail,
  getResumeList,
  parseResume,
  updateResumeName,
  uploadResume,
} from "@/features/resumes/api/resumes";
import { queryKeys } from "@/shared/constants/queryKeys";
import { getApiErrorMessage } from "@/shared/api/error";

export function useResumeListQuery() {
  return useQuery({
    queryKey: queryKeys.resumes.list,
    queryFn: getResumeList,
  });
}

export function useResumeDetailQuery(id?: string) {
  return useQuery({
    queryKey: id ? queryKeys.resumes.detail(id) : ["resumes", "detail", "missing"],
    queryFn: () => getResumeDetail(id!),
    enabled: Boolean(id),
  });
}

export function useParseResumeMutation() {
  return useMutation({
    mutationFn: (file: File) => parseResume(file),
  });
}

export function useUploadResumeMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, name }: { file: File; name: string }) => uploadResume(file, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.resumes.list });
      toast.success("简历上传成功");
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, "简历上传失败"));
    },
  });
}

export function useUpdateResumeMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => updateResumeName(id, name),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.resumes.list });
      queryClient.invalidateQueries({ queryKey: queryKeys.resumes.detail(variables.id) });
      toast.success("简历名称已更新");
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, "更新失败"));
    },
  });
}

export function useDeleteResumeMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteResume(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.resumes.list });
      toast.success("简历已删除");
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, "删除失败"));
    },
  });
}
```

- [ ] **Step 3: Add resume query keys to `frontend/src/shared/constants/queryKeys.ts`**

Add after the existing `evaluation` block:
```typescript
resumes: {
  list: ["resumes", "list"] as const,
  detail: (id: string) => ["resumes", "detail", id] as const,
},
```

- [ ] **Step 4: Create `frontend/src/features/applications/types/application.ts`** (if it doesn't already have StructuredResume type)

Check first — if the type exists, skip. Otherwise create/add the type.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/resumes/ frontend/src/shared/constants/queryKeys.ts
git commit -m "feat: add resume API client and React Query hooks"
```

---

### Task 9: Frontend — ResumeUploader component for ApplyPage

**Files:**
- Create: `frontend/src/features/resumes/components/ResumeUploader.tsx`
- Modify: `frontend/src/pages/ApplyPage.tsx`

- [ ] **Step 1: Create `frontend/src/features/resumes/components/ResumeUploader.tsx`**

```tsx
import { useCallback, useRef, useState } from "react";
import { FileUp, Loader2, CheckCircle2, AlertCircle, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useParseResumeMutation, useResumeListQuery } from "@/features/resumes/hooks/useResumes";
import type { ParseResumeResponse } from "@/features/resumes/api/resumes";
import { cn } from "@/lib/utils";

type UploadStatus = "idle" | "uploading" | "parsed" | "error";

interface ResumeUploaderProps {
  onParsed: (data: ParseResumeResponse) => void;
  onReset?: () => void;
}

const ACCEPTED_TYPES = ".pdf,.docx,.txt";
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

export default function ResumeUploader({ onParsed, onReset }: ResumeUploaderProps) {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [fileName, setFileName] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const parseMutation = useParseResumeMutation();
  const { data: resumeList } = useResumeListQuery();

  const handleFile = useCallback(async (file: File) => {
    // Validate type
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED_TYPES.includes(ext)) {
      setStatus("error");
      setErrorMessage("不支持的文件格式，请上传 PDF、DOCX 或 TXT 文件");
      return;
    }

    // Validate size
    if (file.size > MAX_SIZE) {
      setStatus("error");
      setErrorMessage("文件大小超过 10MB 限制");
      return;
    }

    setFileName(file.name);
    setStatus("uploading");
    setErrorMessage("");

    try {
      const result = await parseMutation.mutateAsync(file);
      setStatus("parsed");
      onParsed(result);
    } catch (error) {
      setStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "简历解析失败，请手动填写");
    }
  }, [parseMutation, onParsed]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset input so same file can be re-selected
    e.target.value = "";
  };

  const handleReset = () => {
    setStatus("idle");
    setFileName("");
    setErrorMessage("");
    onReset?.();
  };

  // Parsed state
  if (status === "parsed") {
    return (
      <Card className="p-4 border-green-200 bg-green-50 dark:bg-green-950/20 dark:border-green-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
            <div>
              <p className="text-sm font-medium text-green-800 dark:text-green-300">
                已从简历自动填充
              </p>
              <p className="text-xs text-green-600 dark:text-green-400">{fileName}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={handleReset}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Drag & drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
          "hover:border-primary hover:bg-primary/5",
          isDragOver && "border-primary bg-primary/10",
          status === "error" && "border-destructive bg-destructive/5",
          status === "uploading" && "border-muted-foreground/30 pointer-events-none opacity-70",
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          className="hidden"
          onChange={handleFileChange}
        />

        {status === "uploading" ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">正在解析简历...</p>
            <p className="text-xs text-muted-foreground">{fileName}</p>
          </div>
        ) : status === "error" ? (
          <div className="flex flex-col items-center gap-2">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="text-sm font-medium text-destructive">解析失败</p>
            <p className="text-xs text-muted-foreground">{errorMessage}</p>
            <Button variant="outline" size="sm" className="mt-2" onClick={(e) => { e.stopPropagation(); handleReset(); }}>
              重新上传
            </Button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <FileUp className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium">
              拖拽简历文件到此处，或<span className="text-primary">点击选择文件</span>
            </p>
            <p className="text-xs text-muted-foreground">
              支持 PDF、DOCX、TXT 格式，最大 10MB
            </p>
          </div>
        )}
      </div>

      {/* Resume library selector */}
      {resumeList && resumeList.items.length > 0 && (
        <div className="text-center">
          <span className="text-xs text-muted-foreground">或</span>
          <div className="mt-2 flex flex-wrap gap-2 justify-center">
            {resumeList.items.map((resume) => (
              <Button
                key={resume.id}
                variant="outline"
                size="sm"
                onClick={async () => {
                  setStatus("uploading");
                  setFileName(resume.file_name);
                  try {
                    const { getResumeDetail } = await import("@/features/resumes/api/resumes");
                    const detail = await getResumeDetail(resume.id);
                    if (detail.structured_data) {
                      setStatus("parsed");
                      onParsed({
                        parsed_text: detail.parsed_text || "",
                        structured_data: detail.structured_data,
                      });
                    }
                  } catch {
                    setStatus("error");
                    setErrorMessage("加载简历失败");
                  }
                }}
              >
                {resume.name}
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Integrate into `frontend/src/pages/ApplyPage.tsx`**

Add import at the top:
```tsx
import ResumeUploader from "@/features/resumes/components/ResumeUploader";
import type { ParseResumeResponse } from "@/features/resumes/api/resumes";
```

Add state near the other useState calls:
```tsx
const [resumeParsed, setResumeParsed] = useState(false);
```

Add the ResumeUploader between the job header and StepForm (after line ~279, before the `{/* Step indicator */}` comment):
```tsx
{/* Resume uploader */}
<ResumeUploader
  onParsed={(data: ParseResumeResponse) => {
    setResumeParsed(true);
    form.reset({
      name: data.structured_data.name || "",
      work_experience_years: data.structured_data.work_experience_years || 0,
      education_level: data.structured_data.education_level || "",
      contact: {
        phone: data.structured_data.contact?.phone || "",
        email: data.structured_data.contact?.email || "",
        wechat: data.structured_data.contact?.wechat || "",
        other: data.structured_data.contact?.other || "",
      },
      work_experience: data.structured_data.work_experience || [],
      project_experience: data.structured_data.project_experience || [],
      education: data.structured_data.education || [],
      certificates: data.structured_data.certificates || [],
      skills: data.structured_data.skills || [],
      self_evaluation: data.structured_data.self_evaluation || "",
    });
    toast.success("简历已自动填充");
  }}
  onReset={() => setResumeParsed(false)}
/>
{resumeParsed && (
  <p className="text-xs text-green-600 dark:text-green-400 text-center -mt-2 mb-2">
    已自动填充表单，请检查并补充完整后提交
  </p>
)}
```

Add a `separator` between uploader and step form:
After the ResumeUploader block, add:
```tsx
<Separator className="my-4" />
```

- [ ] **Step 3: Ensure `StructuredResume` type exists in frontend**

Create or update `frontend/src/features/applications/types/application.ts`:

```typescript
export interface ContactInfo {
  phone?: string | null;
  email?: string | null;
  wechat?: string | null;
  other?: string | null;
}

export interface WorkExperience {
  company: string;
  position: string;
  start_date: string;
  end_date?: string | null;
  description: string;
}

export interface ProjectExperience {
  name: string;
  role: string;
  start_date: string;
  end_date?: string | null;
  description: string;
  technologies: string[];
}

export interface Education {
  school: string;
  major: string;
  degree: string;
  start_date: string;
  end_date?: string | null;
}

export interface Certificate {
  name: string;
  date?: string | null;
}

export interface StructuredResume {
  name: string;
  work_experience_years: number;
  education_level?: string | null;
  contact?: ContactInfo | null;
  work_experience: WorkExperience[];
  project_experience: ProjectExperience[];
  education: Education[];
  certificates: Certificate[];
  skills: string[];
  self_evaluation?: string | null;
}

export interface CreateApplicationPayload {
  job_id: string;
  resume_text: string;
  structured_resume?: StructuredResume;
  cover_letter?: string;
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/resumes/components/ResumeUploader.tsx frontend/src/pages/ApplyPage.tsx frontend/src/features/applications/types/
git commit -m "feat: add ResumeUploader component and integrate into ApplyPage"
```

---

### Task 10: Frontend — SeekerLayout dropdown update (add profile menu item)

**Files:**
- Modify: `frontend/src/shared/ui/layout/SeekerLayout.tsx`

- [ ] **Step 1: Add "个人中心" menu item**

In `SeekerLayout.tsx`, add `User` icon import:
```tsx
import { Briefcase, User } from "lucide-react";
```

In the DropdownMenu, before the "退出登录" item, add:
```tsx
<DropdownMenuItem onClick={() => navigate("/profile")}>
  <User className="h-4 w-4 mr-2" />
  个人中心
</DropdownMenuItem>
<DropdownMenuSeparator />
```

Also import `DropdownMenuSeparator` from shadcn:
```tsx
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/shared/ui/layout/SeekerLayout.tsx
git commit -m "feat: add profile center menu item to seeker layout dropdown"
```

---

### Task 11: Frontend — ProfilePage with resume management

**Files:**
- Create: `frontend/src/pages/ProfilePage.tsx`
- Create: `frontend/src/features/resumes/components/ResumeCard.tsx`

- [ ] **Step 1: Create `frontend/src/features/resumes/components/ResumeCard.tsx`**

```tsx
import { useState } from "react";
import { FileText, Download, Pencil, Trash2, Check, X, File as FileIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ResumeListItem } from "@/features/resumes/api/resumes";
import { useUpdateResumeMutation, useDeleteResumeMutation } from "@/features/resumes/hooks/useResumes";
import { downloadResume } from "@/features/resumes/api/resumes";
import { getApiErrorMessage } from "@/shared/api/error";
import { toast } from "sonner";

interface ResumeCardProps {
  resume: ResumeListItem;
}

function getFileIcon(fileType: string) {
  if (fileType.includes("pdf")) return <FileText className="h-5 w-5 text-red-500" />;
  if (fileType.includes("word") || fileType.includes("docx")) return <FileText className="h-5 w-5 text-blue-500" />;
  return <FileIcon className="h-5 w-5 text-muted-foreground" />;
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr);
  return date.toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" });
}

export default function ResumeCard({ resume }: ResumeCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(resume.name);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const updateMutation = useUpdateResumeMutation();
  const deleteMutation = useDeleteResumeMutation();

  const handleSaveName = async () => {
    if (!editName.trim() || editName.trim() === resume.name) {
      setIsEditing(false);
      return;
    }
    try {
      await updateMutation.mutateAsync({ id: resume.id, name: editName.trim() });
      setIsEditing(false);
    } catch {
      // error handled by hook
    }
  };

  const handleCancelEdit = () => {
    setEditName(resume.name);
    setIsEditing(false);
  };

  const handleDownload = async () => {
    try {
      const data = await downloadResume(resume.id);
      const byteChars = atob(data.file_data);
      const byteNums = new Array(byteChars.length);
      for (let i = 0; i < byteChars.length; i++) {
        byteNums[i] = byteChars.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNums);
      const blob = new Blob([byteArray], { type: data.file_type });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = data.file_name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "下载失败"));
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(resume.id);
      setShowDeleteDialog(false);
    } catch {
      // error handled by hook
    }
  };

  return (
    <>
      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              {getFileIcon(resume.file_type)}
              <div className="flex-1 min-w-0">
                {isEditing ? (
                  <div className="flex items-center gap-1">
                    <Input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="h-7 text-sm"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleSaveName();
                        if (e.key === "Escape") handleCancelEdit();
                      }}
                    />
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleSaveName}>
                      <Check className="h-3.5 w-3.5 text-green-600" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleCancelEdit}>
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ) : (
                  <p className="font-medium text-sm truncate">{resume.name}</p>
                )}
                <p className="text-xs text-muted-foreground truncate mt-0.5">{resume.file_name}</p>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pb-3">
          <p className="text-xs text-muted-foreground">上传于 {formatDate(resume.created_at)}</p>
        </CardContent>
        <CardFooter className="flex gap-1 pt-0">
          <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
            <Pencil className="h-3.5 w-3.5 mr-1" />
            重命名
          </Button>
          <Button variant="ghost" size="sm" onClick={handleDownload}>
            <Download className="h-3.5 w-3.5 mr-1" />
            下载
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setShowDeleteDialog(true)} className="text-destructive hover:text-destructive">
            <Trash2 className="h-3.5 w-3.5 mr-1" />
            删除
          </Button>
        </CardFooter>
      </Card>

      {/* Delete confirmation dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要删除简历「{resume.name}」吗？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? "删除中..." : "确认删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

- [ ] **Step 2: Create `frontend/src/pages/ProfilePage.tsx`**

```tsx
import { useCallback, useRef, useState } from "react";
import { FileUp, Loader2, Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useResumeListQuery, useUploadResumeMutation } from "@/features/resumes/hooks/useResumes";
import ResumeCard from "@/features/resumes/components/ResumeCard";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import { useEffect } from "react";
import { cn } from "@/lib/utils";

const ACCEPTED_TYPES = ".pdf,.docx,.txt";
const MAX_SIZE = 10 * 1024 * 1024;

export default function ProfilePage() {
  const { setItems: setBreadcrumbItems } = useBreadcrumb();

  useEffect(() => {
    setBreadcrumbItems([{ label: "个人中心" }]);
  }, [setBreadcrumbItems]);

  const { data: resumeList, isLoading } = useResumeListQuery();
  const uploadMutation = useUploadResumeMutation();

  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [resumeName, setResumeName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetUpload = () => {
    setResumeName("");
    setSelectedFile(null);
    setIsDragOver(false);
  };

  const handleCloseDialog = () => {
    setShowUploadDialog(false);
    resetUpload();
  };

  const handleFileSelect = (file: File) => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED_TYPES.includes(ext)) {
      toast.error("不支持的文件格式，请上传 PDF、DOCX 或 TXT 文件");
      return;
    }
    if (file.size > MAX_SIZE) {
      toast.error("文件大小超过 10MB 限制");
      return;
    }
    setSelectedFile(file);
    // Auto-generate name from file name
    if (!resumeName) {
      setResumeName(file.name.replace(/\.[^/.]+$/, ""));
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error("请选择简历文件");
      return;
    }
    if (!resumeName.trim()) {
      toast.error("请输入简历名称");
      return;
    }

    try {
      await uploadMutation.mutateAsync({ file: selectedFile, name: resumeName.trim() });
      handleCloseDialog();
    } catch {
      // error handled by hook
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">个人中心</h1>
          <p className="text-sm text-muted-foreground mt-1">管理您的简历档案</p>
        </div>
        <Button onClick={() => setShowUploadDialog(true)}>
          <Plus className="h-4 w-4 mr-1" />
          上传新简历
        </Button>
      </div>

      <Separator className="mb-6" />

      {/* Resume list */}
      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : resumeList && resumeList.items.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {resumeList.items.map((resume) => (
            <ResumeCard key={resume.id} resume={resume} />
          ))}
        </div>
      ) : (
        <Card className="p-12 text-center">
          <FileUp className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground mb-2">暂无简历</p>
          <p className="text-sm text-muted-foreground mb-4">上传您的第一份简历，开始智能投递之旅</p>
          <Button onClick={() => setShowUploadDialog(true)}>
            <Plus className="h-4 w-4 mr-1" />
            上传新简历
          </Button>
        </Card>
      )}

      {/* Upload dialog */}
      <Dialog open={showUploadDialog} onOpenChange={handleCloseDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>上传新简历</DialogTitle>
            <DialogDescription>
              支持 PDF、DOCX、TXT 格式，最大 10MB
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* File drop zone */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
                "hover:border-primary hover:bg-primary/5",
                isDragOver && "border-primary bg-primary/10",
                selectedFile && "border-green-300 bg-green-50 dark:bg-green-950/20 dark:border-green-700",
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_TYPES}
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileSelect(file);
                }}
              />

              {selectedFile ? (
                <div>
                  <p className="text-sm font-medium text-green-700 dark:text-green-300">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-2"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                    }}
                  >
                    重新选择
                  </Button>
                </div>
              ) : (
                <div>
                  <FileUp className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">
                    拖拽文件到此处，或<span className="text-primary">点击选择</span>
                  </p>
                </div>
              )}
            </div>

            {/* Resume name */}
            <div className="space-y-2">
              <Label htmlFor="resume-name">简历名称 <span className="text-destructive">*</span></Label>
              <Input
                id="resume-name"
                placeholder="例如：通用简历、技术岗简历"
                value={resumeName}
                onChange={(e) => setResumeName(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseDialog}>
              取消
            </Button>
            <Button onClick={handleUpload} disabled={!selectedFile || !resumeName.trim() || uploadMutation.isPending}>
              {uploadMutation.isPending ? "上传中..." : "上传并解析"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ProfilePage.tsx frontend/src/features/resumes/components/ResumeCard.tsx
git commit -m "feat: add ProfilePage with resume management"
```

---

### Task 12: Frontend — Add /profile route to App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add import and route**

Add import:
```tsx
import ProfilePage from "@/pages/ProfilePage";
```

Add route inside the SeekerLayout group (after the MyApplicationsPage route):
```tsx
<Route
  path="/profile"
  element={
    <ProtectedRoute role="job_seeker">
      <ProfilePage />
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: add /profile route for resume management"
```

---

### Task 13: Run mypy type check

- [ ] **Step 1: Run mypy**

```bash
cd backend
uv run mypy --strict app/
```

Fix any type errors found.

- [ ] **Step 2: Commit any fixes**

```bash
git add -A
git commit -m "fix: type check fixes"
```

---

### Task 14: Update skeleton.md

- [ ] **Step 1: Update skeleton.md** with new models, services, API routes, and frontend pages.

- [ ] **Step 2: Commit**

```bash
git add skeleton.md
git commit -m "docs: update skeleton.md with resume upload and profile center"
```
