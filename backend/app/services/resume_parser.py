from app.services.placeholder_ai import parse_resume_placeholder


async def parse_resume_document(content: bytes, filename: str) -> dict:
    """解析简历文档（占位实现）"""
    if not content:
        raise ValueError("简历文件为空")
    if not filename:
        raise ValueError("文件名不能为空")

    return await parse_resume_placeholder(filename)
