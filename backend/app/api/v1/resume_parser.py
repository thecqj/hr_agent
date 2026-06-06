from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_required_user
from app.services.resume_parser import parse_resume_document

router = APIRouter(prefix="/resume", tags=["简历解析"])


@router.post("/parse")
async def parse_resume(
    file: UploadFile = File(...),
    current_user=Depends(get_required_user),
):
    """上传简历文件（PDF/Word），返回结构化简历数据（占位实现）。"""
    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="无法读取文件") from exc

    try:
        return await parse_resume_document(content, file.filename or "unknown")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(exc)}") from exc
