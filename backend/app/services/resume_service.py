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