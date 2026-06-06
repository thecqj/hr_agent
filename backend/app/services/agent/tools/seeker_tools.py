from app.services.agent.tools.base import register_tool


@register_tool("analyze_resume_match", "分析简历与岗位匹配度", role="seeker", pages=["/jobs/[id]", "/apply"])
async def analyze_resume_match(job_id: str, resume_text: str, user_id: str | None = None) -> str:
    return "AI 功能暂未启用，匹配分析返回占位结果。"


@register_tool("search_jobs", "搜索岗位", role="seeker", pages=["/jobs"])
async def search_jobs(query: str, user_id: str | None = None) -> str:
    return "AI 功能暂未启用，岗位搜索返回占位结果。"


@register_tool("generate_cover_letter", "生成求职信", role="seeker", pages=["/apply"])
async def generate_cover_letter(job_id: str, style: str = "professional", user_id: str | None = None) -> str:
    return "AI 功能暂未启用，求职信生成返回占位结果。"
