from app.services.agent.tools.base import register_tool
from pydantic import BaseModel, Field

class AnalyzeMatchInput(BaseModel):
    job_id: str = Field(description="岗位ID")
    resume_text: str = Field(description="简历文本")

@register_tool("analyze_resume_match", "分析简历与岗位匹配度", role="seeker", pages=["/jobs/[id]", "/apply"], args_schema=AnalyzeMatchInput)
async def analyze_resume_match(job_id: str, resume_text: str, user_id: str = None) -> str:
    # 模拟分析
    return f"简历与岗位{job_id}的匹配度为85%。技能匹配：Python 90%，FastAPI 80%。"

@register_tool("search_jobs", "搜索岗位", role="seeker", pages=["/jobs"])
async def search_jobs(query: str, user_id: str = None) -> str:
    # 模拟搜索
    return f"根据'{query}'找到3个相关岗位：1. Python后端 2. 全栈工程师 3. 数据分析师"

@register_tool("generate_cover_letter", "生成求职信", role="seeker", pages=["/apply"])
async def generate_cover_letter(job_id: str, style: str = "professional", user_id: str = None) -> str:
    return f"已为您生成{style}风格的求职信草稿。"