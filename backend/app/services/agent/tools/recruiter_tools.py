from app.services.agent.tools.base import register_tool


@register_tool("generate_jd", "根据描述生成完整JD", role="recruiter", pages=["/dashboard/post"])
async def generate_jd(brief: str, user_id: str | None = None) -> str:
    return "AI 功能暂未启用，JD 生成返回占位结果。"


@register_tool("rank_candidates", "对候选人排序", role="recruiter", pages=["/dashboard/applicants/[jobId]"])
async def rank_candidates(job_id: str, user_id: str | None = None) -> str:
    return "AI 功能暂未启用，候选人排序返回占位结果。"
