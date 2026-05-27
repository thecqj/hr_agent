from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.api.deps import get_required_user
from app.services.resume_parser import parse_resume_document

router = APIRouter(prefix="/resume", tags=["简历解析"])

@router.post("/parse")
async def parse_resume(
    file: UploadFile = File(...),
    current_user = Depends(get_required_user),
):
    """上传简历文件（PDF/Word），返回结构化简历数据"""
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="无法读取文件")

    try:
        data = await parse_resume_document(content, file.filename)
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")