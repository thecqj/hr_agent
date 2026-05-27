import json
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from app.database import async_session
from app.models.job import Job
from app.services.agent.state import AgentState, MultiAgentState
from app.services.agent.tools import load_tools_for_context, execute_tool
from app.services.agent.prompts.system import build_system_prompt
from app.config import settings

# ================= 全局 LLM 实例 =================
llm = ChatOpenAI(
    model=settings.AGENT_MODEL,
    temperature=0.3,
    api_key=settings.OPENAI_API_KEY,
    base_url=getattr(settings, "OPENAI_API_BASE", None),
)


# ================= 单智能体节点 =================

async def agent_node(state: AgentState) -> Dict[str, Any]:
    """单智能体核心节点：分析当前状态，决定下一步行动"""
    system_prompt = build_system_prompt(
        user_role=state["user_role"],
        current_page=state["current_page"],
        user_profile=state.get("user_profile"),
        context=state.get("context"),
    )
    tools = load_tools_for_context(state["user_role"], state["current_page"])
    llm_with_tools = llm.bind_tools(tools)
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)

    if response.tool_calls:
        return {
            "messages": [response],
            "next_action": "continue",
            "pending_tool_calls": response.tool_calls,
        }
    else:
        return {
            "messages": [response],
            "next_action": "respond",
            "final_response": response.content,
        }


async def tool_execution_node(state: AgentState) -> Dict[str, Any]:
    """单智能体工具执行节点"""
    tool_messages = []
    for tc in state["pending_tool_calls"]:
        tool_name = tc.get("name")
        tool_args = tc.get("args", {})
        tool_id = tc.get("id")
        try:
            result = await execute_tool(tool_name, tool_args, state["user_id"])
            result_str = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        except Exception as e:
            result_str = f"工具执行出错: {str(e)}"
        tool_messages.append(ToolMessage(content=result_str, tool_call_id=tool_id, name=tool_name))
    return {
        "messages": tool_messages,
        "next_action": "continue",
        "pending_tool_calls": [],
        "iteration_count": state["iteration_count"] + 1,
    }


async def response_node(state: AgentState) -> Dict[str, Any]:
    """单智能体最终响应节点"""
    return {"next_action": "end"}


def should_continue(state: AgentState) -> str:
    """单智能体路由判断"""
    if state["iteration_count"] >= settings.AGENT_MAX_ITERATIONS:
        return "respond"
    if state["next_action"] == "continue":
        return "tools"
    elif state["next_action"] == "respond":
        return "respond"
    return "__end__"


# ================= 多智能体节点 =================

async def supervisor_node(state: MultiAgentState) -> Dict:
    """监督者：根据当前状态决定下一步"""
    supervisor_llm = ChatOpenAI(
        model=settings.AGENT_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY,
        base_url=getattr(settings, "OPENAI_API_BASE", None),
    )
    prompt = f"""你是招聘筛选系统的总调度员。当前任务：为岗位 {state['job_id']} 筛选简历。
当前状态：
- 已获取候选人数量：{len(state.get('candidates', []))}
- 已结构化解析：{len(state.get('structured_candidates', []))}
- 已完成评分：{len(state.get('scores', []))}
- 已生成推荐：{len(state.get('recommendations', []))}
- HR确认状态：{state.get('hr_decision', '未确认')}

请决定下一步动作，从以下选项中选择一个：
- parse: 需要解析简历（如果structured_candidates为空）
- score: 需要评分（如果scores为空）
- rank: 需要排序推荐（如果scores已有但recommendations为空）
- evaluate: 直接评估（跳过解析和排序）
- ask_hr: 需要HR确认推荐结果
- notify: HR已确认，需要执行通知和更新数据库
- end: 任务完成

返回JSON格式：{{"next_action": "选择的操作"}}
"""
    response = await supervisor_llm.ainvoke([HumanMessage(content=prompt)])
    try:
        action = json.loads(response.content)["next_action"]
    except Exception:
        action = "end"
    return {"next_action": action}


async def resume_parser_node(state: MultiAgentState) -> Dict:
    """解析简历，提取结构化信息"""
    parsed = []
    for candidate in state["candidates"]:
        # 模拟解析，实际可调用文档解析智能体
        parsed.append({
            "applicant_id": candidate["id"],
            "skills": ["Python", "React"],
            "experience_years": 3,
            "education": "本科",
            "expected_salary": 15
        })
    return {"structured_candidates": parsed}


async def match_scoring_node(state: MultiAgentState) -> Dict:
    """对每个候选人计算匹配分（旧版简单评分）"""
    scores = []
    for candidate in state["structured_candidates"]:
        score = 0.75  # 模拟分数
        scores.append({"applicant_id": candidate["applicant_id"], "score": score})
    return {"scores": scores}


async def ranking_node(state: MultiAgentState) -> Dict:
    """根据评分排序，生成推荐列表"""
    sorted_candidates = sorted(
        zip(state["candidates"], state["scores"]),
        key=lambda x: x[1]["score"],
        reverse=True
    )
    top_n = sorted_candidates[:5]
    recommendations = []
    for cand, score in top_n:
        recommendations.append({
            "applicant_id": cand["id"],
            "name": cand.get("name", "未知"),
            "score": score["score"],
            "reason": "匹配度高"
        })
    return {"recommendations": recommendations, "next_action": "ask_hr"}


async def hr_review_node(state: MultiAgentState) -> Dict:
    """HR确认节点"""
    return {"next_action": "waiting_hr"}


async def notification_node(state: MultiAgentState) -> Dict:
    """更新数据库并发送通知"""
    return {"next_action": "end", "messages": [AIMessage(content="筛选完成，已标记面试人选")]}


async def evaluate_node(state: MultiAgentState) -> Dict:
    """智能评估节点：根据真实岗位要求为每个候选人打分（0-100）"""
    from openai import AsyncOpenAI
    import json

    # 1. 获取岗位真实信息
    async with async_session() as db:
        job = await db.get(Job, state["job_id"])
        if not job:
            return {"scores": [], "next_action": "end"}

        job_title = job.title
        job_desc = job.description
        job_skills = job.skills_required or []

    skills_str = ", ".join(job_skills) if job_skills else "不限"
    requirements = f"""岗位名称：{job_title}
岗位描述：{job_desc}
所需技能：{skills_str}
"""

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=getattr(settings, "OPENAI_API_BASE", None),
    )

    results = []
    for candidate in state["candidates"]:
        resume = candidate.get("structured_resume") or candidate.get("resume_text", "")
        if isinstance(resume, dict):
            resume = json.dumps(resume, ensure_ascii=False)

        prompt = f"""你是一个严格的招聘评估专家。请根据以下真实的岗位要求，对候选人简历进行客观评分（0-100分），并说明理由。

{requirements}

候选人简历：
{resume}

评分标准：
- 技能匹配度（40%）：与所需技能的重合程度
- 经验匹配度（30%）：相关工作年限和项目经验
- 其他因素（30%）：学历、证书、自我评价等

请返回 JSON 格式：{{"score": 85, "reason": "评分理由，简要说明优缺点"}}
"""
        try:
            resp = await client.chat.completions.create(
                model=settings.AGENT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                timeout=30,
            )
            data = json.loads(resp.choices[0].message.content)
            results.append({
                "applicant_id": candidate["id"],
                "score": int(data.get("score", 0)),
                "reason": data.get("reason", "")
            })
        except Exception as e:
            results.append({
                "applicant_id": candidate["id"],
                "score": 0,
                "reason": f"评估失败: {str(e)[:50]}"
            })

    return {"scores": results, "next_action": "end"}