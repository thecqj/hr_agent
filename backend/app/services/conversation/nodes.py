"""对话 Agent LangGraph 节点实现"""

import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_config

from app.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.deepseek import DeepSeekProvider
from app.models.application import Application, ApplicationStatus
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
from app.models.job import Job, JobStatus
from app.services.agent.state import EvaluationState
from app.services.conversation.state import ConversationState


def _get_db() -> AsyncSession:
    """从 LangGraph config 获取数据库会话"""
    config = get_config()
    db: AsyncSession = config["configurable"]["db"]
    return db


def _get_llm_provider() -> BaseLLMProvider:
    """根据配置获取 LLM 提供商"""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "deepseek":
        return DeepSeekProvider()
    raise ValueError(f"不支持的 LLM 提供商: {provider}")


async def intent_node(state: ConversationState) -> dict[str, Any]:
    """意图识别节点：解析用户消息，提取意图和参数"""
    user_message = state.get("user_message", "")

    await adispatch_custom_event("thinking", {"status": "正在理解您的指令..."})

    provider: BaseLLMProvider | None = None
    try:
        provider = _get_llm_provider()
        result = await provider.recognize_intent(user_message)

        await adispatch_custom_event("intent", {
            "intent": result.intent,
            "params": result.extracted_params,
        })

        return {
            "intent": result.intent,
            "extracted_params": result.extracted_params,
            "clarifying_question": result.clarifying_question,
        }
    except Exception as exc:
        # LLM 意图识别失败时，回退为 unknown
        await adispatch_custom_event("intent", {
            "intent": "unknown",
            "params": {},
        })
        return {
            "intent": "unknown",
            "extracted_params": {},
            "clarifying_question": "抱歉，我暂时无法理解您的意思。输入「帮助」查看我能做什么。",
            "errors": [f"意图识别失败: {exc}"],
        }
    finally:
        if provider is not None:
            await provider.close()


async def dispatch_node(state: ConversationState) -> dict[str, Any]:
    """任务路由节点：根据意图分发到对应工作流"""
    db = _get_db()
    intent = state.get("intent", "unknown")
    current_user_id = state.get("current_user_id", "")
    extracted_params: dict[str, Any] = state.get("extracted_params", {})

    if intent != "evaluate":
        # help 和 unknown 不需要 dispatch
        return {}

    # ── 岗位匹配 ──────────────────────────────────────────
    job_code_param: str | None = extracted_params.get("job_code")
    job_id_param: str | None = extracted_params.get("job_id")
    job_title_param: str | None = extracted_params.get("job_title")

    matched_job: Job | None = None

    # Priority 1: job_code (exact match)
    if job_code_param:
        result = await db.execute(
            select(Job).where(Job.job_code == job_code_param)
        )
        matched_job = result.scalar_one_or_none()
        if matched_job and str(matched_job.recruiter_id) != current_user_id:
            return {
                "reply_message": f"你没有岗位 {job_code_param} 的权限。",
                "errors": [],
            }
        if not matched_job:
            return {
                "reply_message": f"未找到编号为 {job_code_param} 的岗位。",
                "errors": [],
            }

    # Priority 2: job_id (UUID exact match)
    if not matched_job and job_id_param:
        matched_job = await db.get(Job, job_id_param)
        if matched_job and matched_job.recruiter_id != uuid.UUID(current_user_id):
            return {
                "reply_message": "❌ 您不是该岗位的招聘者，无法评估。",
            }

    # Priority 3: job_title (fuzzy match)
    if not matched_job and job_title_param:
        # 模糊匹配岗位标题
        await adispatch_custom_event("progress", {"status": "正在匹配岗位..."})
        escaped_title = str(job_title_param).lower().replace("%", "\\%").replace("_", "\\_")
        stmt = select(Job).where(
            Job.recruiter_id == uuid.UUID(current_user_id),
            Job.status == JobStatus.ACTIVE,
            func.lower(Job.title).ilike(f"%{escaped_title}%", escape="\\"),
        )
        matching_jobs = list((await db.execute(stmt)).scalars().all())

        if len(matching_jobs) == 0:
            # 没找到，列出所有活跃岗位
            all_jobs_stmt = select(Job).where(
                Job.recruiter_id == uuid.UUID(current_user_id),
                Job.status == JobStatus.ACTIVE,
            )
            all_jobs = list((await db.execute(all_jobs_stmt)).scalars().all())
            if all_jobs:
                job_list = "\n".join(f"  {i+1}. {j.title} ({j.job_code})" for i, j in enumerate(all_jobs))
                return {
                    "reply_message": f"❌ 未找到匹配「{job_title_param}」的岗位。您当前有以下活跃岗位：\n{job_list}",
                }
            else:
                return {
                    "reply_message": "❌ 您当前没有活跃的岗位，请先发布岗位。",
                }
        elif len(matching_jobs) > 1:
            job_list = "\n".join(
                f"  {i+1}. {j.title} ({j.job_code})"
                for i, j in enumerate(matching_jobs)
            )
            return {
                "reply_message": f"找到多个匹配「{job_title_param}」的岗位，请指定岗位编号：\n{job_list}",
            }
        else:
            matched_job = matching_jobs[0]

    # No job params provided at all
    if not matched_job and not job_code_param and not job_id_param and not job_title_param:
        active_jobs = await db.execute(
            select(Job).where(
                Job.recruiter_id == uuid.UUID(current_user_id),
                Job.status == JobStatus.ACTIVE,
            ).order_by(Job.created_at.desc())
        )
        jobs_list = active_jobs.scalars().all()
        if not jobs_list:
            return {
                "reply_message": "你当前没有活跃的岗位。",
                "errors": [],
            }
        job_list = "\n".join(
            f"  {j.job_code} - {j.title}"
            for j in jobs_list
        )
        return {
            "reply_message": f"请指定要筛选的岗位：\n{job_list}",
            "errors": [],
        }

    if not matched_job:
        return {
            "reply_message": "❌ 未找到匹配的岗位。",
        }

    # ── interview_quota 写回 ──────────────────────────────────
    user_quota_raw = extracted_params.get("interview_quota")
    if user_quota_raw is not None:
        user_quota = int(user_quota_raw)
        if matched_job.interview_quota != user_quota:
            matched_job.interview_quota = user_quota
            await db.commit()
            await db.refresh(matched_job)

    # ── 并发检查 ──────────────────────────────────────────
    existing_stmt = select(EvaluationTask).where(
        EvaluationTask.job_id == matched_job.id,
        EvaluationTask.status.in_([EvalTaskStatus.PENDING, EvalTaskStatus.RUNNING]),
    )
    existing_task = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing_task:
        return {
            "task_id": str(existing_task.id),
            "evaluation_status": existing_task.status.value,
            "reply_message": f"⚠️ 岗位「{matched_job.title}」已有正在进行的评估任务。",
            "reply_cards": [{
                "type": "evaluation_summary",
                "task_id": str(existing_task.id),
                "job_title": matched_job.title,
                "total_count": existing_task.total_count,
                "recommended_count": 0,
                "rejected_count": 0,
                "result_page_url": f"/dashboard/evaluation/{existing_task.id}",
            }],
        }

    # ── 创建评估任务 ──────────────────────────────────────
    interview_quota = extracted_params.get("interview_quota") or matched_job.interview_quota

    # 统计 pending 申请数
    job_uuid = matched_job.id
    count_stmt = select(func.count()).select_from(Application).where(
        Application.job_id == job_uuid,
        Application.status == ApplicationStatus.PENDING,
    )
    pending_count: int = (await db.execute(count_stmt)).scalar() or 0

    if pending_count == 0:
        return {
            "reply_message": f"❌ 岗位「{matched_job.title}」暂无待处理的简历。",
        }

    # 创建任务记录
    task_id = uuid.uuid4()
    eval_task = EvaluationTask(
        id=task_id,
        job_id=job_uuid,
        triggered_by=uuid.UUID(current_user_id),
        status=EvalTaskStatus.PENDING,
        total_count=pending_count,
    )
    db.add(eval_task)
    await db.commit()
    await db.refresh(eval_task)
    task_id_str = str(task_id)

    # ── 内联执行评估图 ──────────────────────────────────
    await adispatch_custom_event("progress", {
        "status": f"正在评估「{matched_job.title}」岗位的简历...",
        "total_count": pending_count,
    })

    from app.database import get_checkpointer
    from app.services.agent.graph import build_evaluation_graph

    checkpointer = get_checkpointer()
    graph = build_evaluation_graph(checkpointer)

    initial_state: EvaluationState = {
        "job_id": str(matched_job.id),
        "triggered_by": current_user_id,
        "task_id": task_id_str,
        "errors": [],
        "interview_quota_override": interview_quota if isinstance(interview_quota, int) else None,
    }

    config: RunnableConfig = {
        "configurable": {
            "thread_id": task_id_str,
            "db": db,
        }
    }

    try:
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            if event.get("event") == "on_custom_event":
                event_data = event.get("data", {})
                await adispatch_custom_event("progress", event_data)
    except Exception as exc:
        failed_task = await db.get(EvaluationTask, task_id_str)
        if failed_task and failed_task.status not in (
            EvalTaskStatus.COMPLETED, EvalTaskStatus.CONFIRMED, EvalTaskStatus.FAILED,
        ):
            failed_task.status = EvalTaskStatus.FAILED
            failed_task.error_message = f"评估工作流异常: {exc}"
            await db.commit()
        return {
            "task_id": task_id_str,
            "evaluation_status": "failed",
            "reply_message": f"❌ 评估工作流执行出错：{exc}",
            "errors": [f"评估工作流异常: {exc}"],
        }

    final_task = await db.get(EvaluationTask, task_id_str)
    eval_status = final_task.status.value if final_task else "unknown"

    return {
        "task_id": task_id_str,
        "evaluation_status": eval_status,
    }


async def feedback_node(state: ConversationState) -> dict[str, Any]:
    """结果反馈节点：格式化结果摘要"""
    db = _get_db()
    intent = state.get("intent", "unknown")

    # 如果 dispatch_node 已经设置了 reply_message，直接使用
    if state.get("reply_message"):
        return {}

    # evaluate 意图
    if intent == "evaluate":
        task_id = state.get("task_id")
        if not task_id:
            return {"reply_message": "❌ 评估任务创建失败，请重试。"}

        task = await db.get(EvaluationTask, task_id)
        if not task:
            return {"reply_message": "❌ 评估任务不存在。"}

        job = await db.get(Job, task.job_id)
        job_title = job.title if job else "未知岗位"

        if task.status == EvalTaskStatus.COMPLETED:
            summary = task.result_summary or {}
            recommend_count = summary.get("recommend_count", 0)
            reject_count = summary.get("reject_count", 0)

            return {
                "reply_message": f"✅ 已完成「{job_title}」岗位的简历评估，共 {task.total_count} 份简历，推荐 {recommend_count} 人进入面试。",
                "reply_cards": [{
                    "type": "evaluation_summary",
                    "task_id": task_id,
                    "job_title": job_title,
                    "total_count": task.total_count,
                    "recommended_count": recommend_count,
                    "rejected_count": reject_count,
                    "result_page_url": f"/dashboard/evaluation/{task_id}",
                }],
                "result_page_url": f"/dashboard/evaluation/{task_id}",
            }
        elif task.status == EvalTaskStatus.FAILED:
            return {
                "reply_message": f"❌ 评估失败：{task.error_message or '未知错误'}",
            }
        else:
            return {
                "reply_message": f"⏳ 评估任务状态：{task.status.value}，请稍后查看。",
            }

    # help 意图
    if intent == "help":
        return {
            "reply_message": "我可以帮您完成以下操作：\n\n• **筛选岗位简历** — 如「帮我筛选前端开发岗位的简历」\n• **指定进面人数** — 如「前端岗位选 5 人进面试」\n\n输入自然语言指令即可，我会理解您的意图并执行。",
        }

    # unknown 意图
    clarifying = state.get("clarifying_question")
    return {
        "reply_message": clarifying or "抱歉，我没有理解您的意思。输入「帮助」查看我能做什么。",
    }


def route_by_intent(state: ConversationState) -> str:
    """条件路由：根据意图决定下一个节点"""
    intent = state.get("intent", "unknown")
    if intent == "evaluate":
        return "dispatch"
    return "feedback"
