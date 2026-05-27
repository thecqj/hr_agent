from app.services.agent.tools.base import register_tool

@register_tool("generate_jd", "根据描述生成完整JD", role="recruiter", pages=["/dashboard/post"])
async def generate_jd(brief: str, user_id: str = None) -> str:
    return f"基于'{brief}'，已为您生成包含职责、要求的JD草稿。"

@register_tool("rank_candidates", "对候选人排序", role="recruiter", pages=["/dashboard/applicants/[jobId]"])
async def rank_candidates(job_id: str, user_id: str = None) -> str:
    return f"已对岗位{job_id}的候选人按匹配度排序，前3名为：张三(92%)、李四(85%)、王五(78%)。"