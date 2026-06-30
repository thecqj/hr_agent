"""对话 Agent LangGraph 节点实现"""

import time
import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_config

from app.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.deepseek import DeepSeekProvider
from app.models.application import Application, ApplicationStatus
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
from app.models.job import Job, JobStatus
from app.models.user import User
from app.services.agent.state import EvaluationState
from app.services.conversation.state import ConversationState, PendingAction
from app.schemas.application import ApplicationStatusUpdateRequest
from app.schemas.job import JobStatusUpdateRequest
from app.services.job_service import resolve_job, list_jobs as svc_list_jobs, update_job_status
from app.services.application_service import (
    count_by_job_and_status,
    count_by_job_grouped_by_status,
    list_by_job,
    update_application_status,
)


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


def _build_context_prompt(state: ConversationState) -> str | None:
    """从 state 中构建上下文提示词，用于意图识别

    如果没有上下文信息，返回 None（退化为单轮模式）。
    """
    session_summary: str | None = state.get("session_summary")
    context_entities: dict[str, Any] | None = state.get("context_entities")
    chat_history: list[dict[str, Any]] | None = state.get("chat_history")

    parts: list[str] = []

    if session_summary:
        parts.append(f"[对话摘要]\n{session_summary}")

    if context_entities and any(context_entities.values()):
        entity_lines = [f"  {k}: {v}" for k, v in context_entities.items() if v]
        if entity_lines:
            parts.append(f"[当前对话实体]\n" + "\n".join(entity_lines))

    # Take the last 5 turns from chat_history
    if chat_history and len(chat_history) > 0:
        recent_turns = chat_history[-5:]
        history_lines = []
        for t in recent_turns:
            role_label = "用户" if t["role"] == "user" else "助手"
            history_lines.append(f"  {role_label}: {t['content']}")
        parts.append("[最近对话]\n" + "\n".join(history_lines))

    if not parts:
        return None

    return "\n\n".join(parts)


def _update_context_entities(
    state: ConversationState,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Merge entity updates into context_entities and return the updated dict"""
    existing: dict[str, Any] = dict(state.get("context_entities", {}) or {})
    existing.update(updates)
    return {"context_entities": existing}


async def intent_node(state: ConversationState) -> dict[str, Any]:
    """意图识别节点：解析用户消息，提取意图和参数（支持多轮上下文）"""
    user_message = state.get("user_message", "")

    await adispatch_custom_event("thinking", {"status": "正在理解您的指令..."})

    # Build context prompt from state
    context_prompt = _build_context_prompt(state)

    provider: BaseLLMProvider | None = None
    try:
        provider = _get_llm_provider()
        result = await provider.recognize_intent(user_message, context_prompt=context_prompt)

        extracted_params = result.extracted_params

        # Merge missing params from context_entities
        # Nodes store entities with "current_" prefix (e.g. current_job_code),
        # but extracted_params uses the shorter form (e.g. job_code).
        context_entities: dict[str, Any] = state.get("context_entities", {})
        _ENTITY_TO_PARAM_MAP: dict[str, str] = {
            "current_job_code": "job_code",
            "current_job_id": "job_id",
            "current_candidate_name": "candidate_name",
        }
        if context_entities:
            for entity_key, param_key in _ENTITY_TO_PARAM_MAP.items():
                if param_key not in extracted_params and context_entities.get(entity_key):
                    extracted_params[param_key] = context_entities[entity_key]

        await adispatch_custom_event("intent", {
            "intent": result.intent,
            "params": extracted_params,
        })

        return {
            "intent": result.intent,
            "extracted_params": extracted_params,
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
            **_update_context_entities(state, {"current_job_id": str(matched_job.id), "current_job_code": matched_job.job_code, "task_id": str(existing_task.id)}),
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
        **_update_context_entities(state, {"current_job_id": str(matched_job.id), "current_job_code": matched_job.job_code, "task_id": task_id_str}),
    }


# ── 查询类节点 ─────────────────────────────────────────────


async def list_jobs_node(state: ConversationState) -> dict[str, Any]:
    """岗位列表查询节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    status_filter: str | None = params.get("status_filter", "active")

    user = await db.get(User, uuid.UUID(current_user_id))
    if user is None:
        return {"reply_message": "❌ 用户不存在。"}

    jobs, total = await svc_list_jobs(
        db=db,
        status=status_filter,
        current_user=user,
    )

    if not jobs:
        return {
            "reply_message": f"当前没有{'活跃' if status_filter == 'active' else ''}岗位。",
        }

    job_items = [
        {
            "job_code": j.job_code,
            "title": j.title,
            "status": j.status.value,
            "head_count": j.head_count,
        }
        for j in jobs
    ]

    job_lines = "\n".join(f"  {j.job_code} - {j.title}（{j.status.value}，编制 {j.head_count} 人）" for j in jobs)

    return {
        "reply_message": f"共 {total} 个岗位：\n{job_lines}",
        "reply_cards": [{"type": "job_list", "jobs": job_items}],
    }


async def job_detail_node(state: ConversationState) -> dict[str, Any]:
    """岗位详情查询节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    job_code = params.get("job_code")
    job_title = params.get("job_title")
    detail_scope = params.get("detail_scope", "full")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return {"reply_message": "❌ 未找到匹配的岗位。"}

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}

    job = resolved

    if detail_scope == "full":
        job_data = {
            "job_code": job.job_code,
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements,
            "skills_required": job.skills_required or [],
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "location": job.location,
            "work_type": job.work_type.value,
            "head_count": job.head_count,
            "interview_quota": job.interview_quota,
            "status": job.status.value,
        }
        return {
            "reply_message": f"📋 岗位「{job.title}」({job.job_code})详情：",
            "reply_cards": [{"type": "job_detail", "job": job_data}],
            **_update_context_entities(state, {"current_job_id": str(job.id), "current_job_code": job.job_code}),
        }

    # Scoped detail
    scope_map: dict[str, tuple[str, str]] = {
        "responsibilities": ("岗位职责", job.description),
        "requirements": ("任职要求", job.requirements),
        "skills": ("技能要求", ", ".join(job.skills_required or [])),
        "quota": ("招聘指标", f"编制 {job.head_count} 人，进面名额 {job.interview_quota} 人"),
    }
    label, content = scope_map.get(detail_scope, ("详情", job.description))
    return {
        "reply_message": f"📋 {job.title}({job.job_code}) — {label}：\n{content}",
        **_update_context_entities(state, {"current_job_id": str(job.id), "current_job_code": job.job_code}),
    }


async def pending_count_node(state: ConversationState) -> dict[str, Any]:
    """待审核简历计数节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    job_code = params.get("job_code")
    job_title = params.get("job_title")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return {"reply_message": "❌ 未找到匹配的岗位。"}

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}

    job = resolved
    count = await count_by_job_and_status(db, str(job.id), "pending")

    if count == 0:
        return {
            "reply_message": f"📋 岗位「{job.title}」({job.job_code})暂无待审核简历。",
            **_update_context_entities(state, {"current_job_id": str(job.id), "current_job_code": job.job_code}),
        }
    return {
        "reply_message": f"📋 岗位「{job.title}」({job.job_code})有 {count} 份待审核简历。",
        **_update_context_entities(state, {"current_job_id": str(job.id), "current_job_code": job.job_code}),
    }


async def interview_count_node(state: ConversationState) -> dict[str, Any]:
    """面试中候选人计数节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    job_code = params.get("job_code")
    job_title = params.get("job_title")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return {"reply_message": "❌ 未找到匹配的岗位。"}

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}

    job = resolved
    count = await count_by_job_and_status(db, str(job.id), "interview")

    if count == 0:
        return {
            "reply_message": f"📋 岗位「{job.title}」({job.job_code})暂无面试中的候选人。",
            **_update_context_entities(state, {"current_job_id": str(job.id), "current_job_code": job.job_code}),
        }
    return {
        "reply_message": f"📋 岗位「{job.title}」({job.job_code})有 {count} 位候选人正在面试中。",
        **_update_context_entities(state, {"current_job_id": str(job.id), "current_job_code": job.job_code}),
    }


async def candidate_eval_node(state: ConversationState) -> dict[str, Any]:
    """候选人 AI 评估结果查询节点"""
    db = _get_db()
    params: dict[str, Any] = state.get("extracted_params", {})

    application_id = params.get("application_id")
    candidate_name = params.get("candidate_name", "")

    app: Application | None = None
    if application_id:
        app = await db.get(Application, application_id)

    if not app:
        # 尝试按候选人姓名 + job_code 查找
        job_code = params.get("job_code")
        if job_code:
            job_resolved = await resolve_job(db, state.get("current_user_id", ""), job_code=job_code)
            if isinstance(job_resolved, list):
                job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in job_resolved)
                return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}
            if job_resolved:
                escaped_name = candidate_name.lower().replace("%", "\\%").replace("_", "\\_")
                name_stmt = select(Application).join(
                    User, Application.applicant_id == User.id
                ).where(
                    Application.job_id == job_resolved.id,
                    User.name.ilike(f"%{escaped_name}%", escape="\\"),
                ).options(selectinload(Application.applicant))
                app_result = await db.execute(name_stmt)
                apps = list(app_result.scalars().all())
                if len(apps) == 1:
                    app = apps[0]
                elif len(apps) > 1:
                    return {"reply_message": f"找到 {len(apps)} 位名为「{candidate_name}」的候选人，请指定申请 ID。"}

        if not app:
            return {"reply_message": f"❌ 未找到候选人「{candidate_name}」的申请记录。"}

    # Build response
    name = app.applicant.name if app.applicant else candidate_name
    score_str = f"{app.ai_score}" if app.ai_score is not None else "未评估"
    decision_str = {"recommend": "推荐", "reject": "不推荐"}.get(str(app.ai_decision), str(app.ai_decision or "未评估"))
    reason_str = app.ai_decision_reason or "无"
    status_str = {"pending": "待审核", "interview": "面试中", "rejected": "已拒绝", "hired": "已录用"}.get(app.status.value, app.status.value)

    return {
        "reply_message": f"📋 候选人「{name}」评估结果：\n• AI 评分：{score_str}\n• AI 决策：{decision_str}\n• 决策原因：{reason_str}\n• 当前状态：{status_str}",
        **_update_context_entities(state, {"current_candidate_name": name, "current_job_id": str(app.job_id) if app.job_id else None}),
    }


async def funnel_node(state: ConversationState) -> dict[str, Any]:
    """招聘漏斗/进度概览节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    job_code = params.get("job_code")
    job_title = params.get("job_title")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return {"reply_message": "❌ 未找到匹配的岗位。"}

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}

    job = resolved
    grouped = await count_by_job_grouped_by_status(db, str(job.id))

    total = sum(grouped.values())
    if total == 0:
        return {
            "reply_message": f"📋 岗位「{job.title}」({job.job_code})暂无投递记录。",
            **_update_context_entities(state, {"current_job_id": str(job.id), "current_job_code": job.job_code}),
        }

    stages = []
    status_labels = {"pending": "待审核", "interview": "面试中", "rejected": "已拒绝", "hired": "已录用"}
    for status_key in ["pending", "interview", "rejected", "hired"]:
        count = grouped.get(status_key, 0)
        stages.append({
            "status": status_labels.get(status_key, status_key),
            "count": count,
            "percentage": round(count / total * 100, 1),
        })

    return {
        "reply_message": f"📋 岗位「{job.title}」({job.job_code})招聘进度：共收到 {total} 份简历",
        "reply_cards": [{
            "type": "funnel",
            "job_code": job.job_code,
            "job_title": job.title,
            "stages": stages,
        }],
        **_update_context_entities(state, {"current_job_id": str(job.id), "current_job_code": job.job_code}),
    }


async def candidate_list_node(state: ConversationState) -> dict[str, Any]:
    """候选人列表查询节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    job_code = params.get("job_code")
    job_title = params.get("job_title")
    decision_filter = params.get("decision_filter", "recommend")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return {"reply_message": "❌ 未找到匹配的岗位。"}

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}

    job = resolved
    apps = await list_by_job(db, str(job.id), decision_filter=decision_filter if decision_filter != "all" else None)

    if not apps:
        filter_label = "AI 推荐" if decision_filter == "recommend" else ""
        return {
            "reply_message": f"📋 岗位「{job.title}」({job.job_code})暂无{filter_label}候选人。",
            **_update_context_entities(state, {"current_job_id": str(job.id), "current_job_code": job.job_code}),
        }

    candidates = [
        {
            "name": a.applicant.name if a.applicant else "未知",
            "ai_score": a.ai_score,
            "ai_decision": a.ai_decision,
            "status": a.status.value,
        }
        for a in apps
    ]

    filter_label = "AI 推荐" if decision_filter == "recommend" else "全部"
    return {
        "reply_message": f"📋 岗位「{job.title}」({job.job_code}){filter_label}候选人 {len(candidates)} 人：",
        "reply_cards": [{
            "type": "candidate_list",
            "job_code": job.job_code,
            "job_title": job.title,
            "candidates": candidates,
        }],
        **_update_context_entities(state, {"current_job_id": str(job.id), "current_job_code": job.job_code}),
    }


async def feedback_node(state: ConversationState) -> dict[str, Any]:
    """结果反馈节点：格式化结果摘要 + 更新对话历史 + 摘要压缩"""
    db = _get_db()
    intent = state.get("intent", "unknown")
    reply_message = state.get("reply_message", "")

    # ── pending_action 冲突处理 ──────────────────────────────
    reply_message_payload: str = ""
    if reply_message:
        pending = state.get("pending_action")
        if pending and intent not in ("confirm", "cancel", "status_change", "job_status"):
            reply_message_payload = reply_message + "\n（已取消待确认操作）"
            pending_action_payload: PendingAction | None = None
        else:
            reply_message_payload = reply_message
            pending_action_payload = state.get("pending_action")
    else:
        pending_action_payload = state.get("pending_action")

    # ── 构建反馈消息（保留原有逻辑）──────────────────────────
    if not reply_message_payload:
        # evaluate 意图
        if intent == "evaluate":
            task_id = state.get("task_id")
            if not task_id:
                reply_message_payload = "❌ 评估任务创建失败，请重试。"
            else:
                task = await db.get(EvaluationTask, task_id)
                if not task:
                    reply_message_payload = "❌ 评估任务不存在。"
                else:
                    job = await db.get(Job, task.job_id)
                    job_title = job.title if job else "未知岗位"

                    if task.status == EvalTaskStatus.COMPLETED:
                        summary = task.result_summary or {}
                        recommend_count = summary.get("recommend_count", 0)
                        reject_count = summary.get("reject_count", 0)
                        reply_message_payload = f"✅ 已完成「{job_title}」岗位的简历评估，共 {task.total_count} 份简历，推荐 {recommend_count} 人进入面试。"
                    elif task.status == EvalTaskStatus.FAILED:
                        reply_message_payload = f"❌ 评估失败：{task.error_message or '未知错误'}"
                    else:
                        reply_message_payload = f"⏳ 评估任务状态：{task.status.value}，请稍后查看。"

        elif intent == "help":
            reply_message_payload = (
                "我可以帮您完成以下操作：\n\n"
                "📋 **岗位管理**\n"
                "• 「有哪些活跃岗位？」— 查询岗位列表\n"
                "• 「J001的任职要求」— 查看岗位详情\n"
                "• 「帮我关闭 J001」— 关闭岗位\n"
                "• 「发布 J001」— 重新发布岗位\n\n"
                "📊 **招聘进度**\n"
                "• 「J001还有多少简历没看？」— 待审核简历数\n"
                "• 「J001有几个人在面试？」— 面试中人数\n"
                "• 「J001的招聘进度」— 漏斗概览\n\n"
                "👥 **候选人管理**\n"
                "• 「J001推荐的候选人」— 候选人列表\n"
                "• 「张三的评估结果」— AI 评估详情\n"
                "• 「把张三推进到面试」— 变更候选人状态\n\n"
                "🔍 **简历筛选**\n"
                "• 「帮我筛选前端岗位的简历」— AI 筛选简历\n"
                "• 「前端岗位选5人进面试」— 指定进面人数"
            )
        elif intent == "cancel":
            reply_message_payload = "✅ 已取消。"
        else:
            clarifying = state.get("clarifying_question")
            reply_message_payload = clarifying or "抱歉，我没有理解您的意思。输入「帮助」查看我能做什么。"

    # ── 更新 chat_history ────────────────────────────────────
    chat_history: list[dict[str, Any]] = list(state.get("chat_history") or [])
    chat_history.append({
        "role": "user",
        "content": state.get("user_message", ""),
        "timestamp": time.time(),
    })
    chat_history.append({
        "role": "assistant",
        "content": reply_message_payload,
        "timestamp": time.time(),
    })

    # ── 摘要压缩 ────────────────────────────────────────────
    session_summary: str | None = state.get("session_summary")
    SUMMARY_THRESHOLD = 10  # 超过 10 轮时压缩

    if len(chat_history) > SUMMARY_THRESHOLD:
        provider: BaseLLMProvider | None = None
        try:
            provider = _get_llm_provider()
            # 压缩前 5 轮（最旧的 5 条消息 = 2-3 对话轮次）
            old_turns = chat_history[:5]
            new_summary = await provider.summarize_conversation(
                [{"role": t["role"], "content": t["content"]} for t in old_turns],
                existing_summary=session_summary,
            )
            # 截断到 500 字
            if len(new_summary) > 500:
                new_summary = new_summary[:500]
            session_summary = new_summary
            # 保留最近 5 轮
            chat_history = chat_history[5:]
        except Exception:
            # 摘要失败不阻塞，保留原始历史
            pass
        finally:
            if provider is not None:
                await provider.close()

    result: dict[str, Any] = {
        "reply_message": reply_message_payload,
        "chat_history": chat_history,
        "session_summary": session_summary,
        "reply_cards": None,  # Clear cards from previous turns
    }

    if pending_action_payload is not None or state.get("pending_action") is not None:
        result["pending_action"] = pending_action_payload

    return result


# ── 确认 / 操作类节点 ────────────────────────────────────────────

_STATUS_LABELS: dict[str, str] = {
    "pending": "待审核",
    "interview": "面试阶段",
    "rejected": "已拒绝",
    "hired": "已录用",
}

_JOB_ACTION_LABELS: dict[str, str] = {
    "open": "开启",
    "close": "关闭",
}


async def confirm_node(state: ConversationState) -> dict[str, Any]:
    """确认节点：为写操作生成确认提示"""
    intent = state.get("intent", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    if intent == "status_change":
        # Resolve candidate_name to application_id if not already provided
        if not params.get("application_id"):
            candidate_name = params.get("candidate_name", "")
            job_code = params.get("job_code")

            if candidate_name and job_code:
                db = _get_db()
                current_user_id = state.get("current_user_id", "")

                # Resolve job first
                job_resolved = await resolve_job(db, current_user_id, job_code=job_code)
                if isinstance(job_resolved, list):
                    job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in job_resolved)
                    return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}

                if job_resolved:
                    # Look up application by candidate name + job
                    escaped_name = candidate_name.lower().replace("%", "\\%").replace("_", "\\_")
                    name_stmt = select(Application).join(
                        User, Application.applicant_id == User.id
                    ).where(
                        Application.job_id == job_resolved.id,
                        User.name.ilike(f"%{escaped_name}%", escape="\\"),
                    ).options(selectinload(Application.applicant))
                    app_result = await db.execute(name_stmt)
                    apps = list(app_result.scalars().all())

                    if len(apps) == 1:
                        params = {**params, "application_id": str(apps[0].id)}
                    elif len(apps) > 1:
                        return {
                            "reply_message": f"找到 {len(apps)} 位名为「{candidate_name}」的候选人，请指定申请 ID。",
                        }
                    else:
                        return {
                            "reply_message": f"❌ 未找到候选人「{candidate_name}」的申请记录。",
                        }

        candidate_name = params.get("candidate_name", "未知候选人")
        target_status = params.get("target_status", "")
        status_label = _STATUS_LABELS.get(target_status, target_status)
        action_text = f"将候选人「{candidate_name}」推进到{status_label}"
    elif intent == "job_status":
        job_code = params.get("job_code", "")
        action = params.get("action", "")
        action_label = _JOB_ACTION_LABELS.get(action, action)
        action_text = f"{action_label}岗位 {job_code}"
    else:
        action_text = "执行该操作"

    return {
        "reply_message": f"⚠️ 请确认：{action_text}？\n回复「确认」执行，「取消」放弃。",
        "reply_cards": [{"type": "confirm", "action": action_text, "params": params}],
        "pending_action": {"intent": intent, "params": params},
    }


async def cancel_node(state: ConversationState) -> dict[str, Any]:
    """取消节点：清除待确认操作"""
    return {
        "reply_message": "✅ 已取消操作。",
        "pending_action": None,
    }


async def status_change_node(state: ConversationState) -> dict[str, Any]:
    """候选人状态变更执行节点"""
    pending = state.get("pending_action")
    if not pending:
        return {
            "reply_message": "❌ 没有待执行的操作。",
            "pending_action": None,
        }

    params: dict[str, Any] = pending.get("params", {})
    application_id = params.get("application_id")
    target_status = params.get("target_status", "")

    if not application_id:
        return {
            "reply_message": "❌ 缺少申请 ID，无法执行状态变更。",
            "pending_action": None,
        }

    db = _get_db()
    current_user_id = state.get("current_user_id", "")

    try:
        user = await db.get(User, uuid.UUID(current_user_id))
        if user is None:
            return {
                "reply_message": "❌ 用户不存在。",
                "pending_action": None,
            }
        status_enum = ApplicationStatus(target_status)
        data = ApplicationStatusUpdateRequest(status=status_enum)
        await update_application_status(db, application_id, data, user)

        status_label = _STATUS_LABELS.get(target_status, target_status)
        name = params.get("candidate_name", "未知候选人")
        return {
            "reply_message": f"✅ 已将候选人「{name}」推进到{status_label}。",
            "pending_action": None,
            **_update_context_entities(state, {"current_candidate_name": name}),
        }
    except Exception as exc:
        return {
            "reply_message": f"❌ 状态变更失败：{exc}",
            "pending_action": None,
            "errors": [f"状态变更失败: {exc}"],
        }


async def job_status_action_node(state: ConversationState) -> dict[str, Any]:
    """岗位状态变更执行节点"""
    pending = state.get("pending_action")
    if not pending:
        return {
            "reply_message": "❌ 没有待执行的操作。",
            "pending_action": None,
        }

    params: dict[str, Any] = pending.get("params", {})
    job_code = params.get("job_code")
    job_title = params.get("job_title")
    action = params.get("action", "")

    db = _get_db()
    current_user_id = state.get("current_user_id", "")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return {
            "reply_message": "❌ 未找到匹配的岗位。",
            "pending_action": None,
        }

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {
            "reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}",
            "pending_action": None,
        }

    job = resolved

    action_to_status: dict[str, JobStatus] = {
        "open": JobStatus.ACTIVE,
        "close": JobStatus.CLOSED,
    }
    target_status = action_to_status.get(action)
    if target_status is None:
        return {
            "reply_message": f"❌ 不支持的操作类型：{action}",
            "pending_action": None,
        }

    try:
        user = await db.get(User, uuid.UUID(current_user_id))
        if user is None:
            return {
                "reply_message": "❌ 用户不存在。",
                "pending_action": None,
            }
        data = JobStatusUpdateRequest(status=target_status)
        await update_job_status(db, str(job.id), data, user)

        action_label = _JOB_ACTION_LABELS.get(action, action)
        return {
            "reply_message": f"✅ 已{action_label}岗位「{job.title}」({job.job_code})。",
            "pending_action": None,
            **_update_context_entities(state, {"current_job_id": str(job.id), "current_job_code": job.job_code}),
        }
    except Exception as exc:
        return {
            "reply_message": f"❌ 岗位状态变更失败：{exc}",
            "pending_action": None,
            "errors": [f"岗位状态变更失败: {exc}"],
        }


_QUERY_INTENTS = frozenset({
    "list_jobs",
    "job_detail",
    "pending_count",
    "interview_count",
    "candidate_eval",
    "funnel",
    "candidate_list",
})

_CONFIRM_REQUIRED_INTENTS = frozenset({
    "status_change",
    "job_status",
})


def route_by_intent(state: ConversationState) -> str:
    """条件路由：根据意图决定下一个节点"""
    intent = state.get("intent", "unknown")

    # 简历评估 → dispatch
    if intent == "evaluate":
        return "dispatch"

    # 查询类意图 → 对应节点名
    if intent in _QUERY_INTENTS:
        return intent

    # 操作类意图 → 确认节点
    if intent in _CONFIRM_REQUIRED_INTENTS:
        return "confirm"

    # 用户确认 → 执行节点（若有待确认操作）或反馈
    if intent == "confirm":
        pending = state.get("pending_action")
        if pending:
            return "execute_action"
        return "feedback"

    # 用户取消 → 取消节点
    if intent == "cancel":
        return "cancel"

    # help / unknown → 反馈
    return "feedback"


def route_by_pending_action(state: ConversationState) -> str:
    """根据 pending_action 的 intent 类型路由到具体执行节点"""
    pending = state.get("pending_action")
    action_intent = pending.get("intent", "") if pending else ""

    if action_intent == "status_change":
        return "status_change"
    elif action_intent == "job_status":
        return "job_status_action"
    return "feedback"
