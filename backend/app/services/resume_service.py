import io
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status

from app.llm.deepseek import DeepSeekProvider

ALLOWED_CONTENT_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/octet-stream",
}

# File signature magic bytes for type detection
PDF_MAGIC = b"%PDF"
DOCX_MAGIC = b"PK\x03\x04"

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


def _detect_file_type(file_bytes: bytes, content_type: str) -> str | None:
    """通过 magic bytes 检测文件真实类型，兜底使用 content_type"""
    if content_type in ("application/pdf",) or file_bytes.startswith(PDF_MAGIC):
        return "application/pdf"
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file_bytes.startswith(DOCX_MAGIC):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if content_type in ("text/plain", "application/octet-stream"):
        return "text/plain"
    return None


async def parse_resume_file(file: UploadFile) -> tuple[bytes, str, dict[str, object]]:
    """上传并解析简历文件，返回 (file_bytes, parsed_text, structured_data)

    NOTE: 此函数会消耗 file 流，调用方不应再读取 file。
    """
    content_type = file.content_type or "application/octet-stream"

    # 读取文件内容（一次性消耗流）
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

    # 通过文件内容（magic bytes）检测真实类型
    detected_type = _detect_file_type(file_bytes, content_type)
    if detected_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型，仅支持 PDF、DOCX、TXT",
        )

    # 提取文本
    try:
        parsed_text = await extract_text(file_bytes, detected_type)
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

    return file_bytes, parsed_text, structured_data