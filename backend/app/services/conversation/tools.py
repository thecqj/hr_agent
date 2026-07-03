"""HR Agent ReAct 对话 — Tool 定义

7 个 Tool: 3 个通用查询 + 4 个写操作
"""

import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.config import get_config

from app.models.application import Application, ApplicationStatus
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
from app.models.job import Job, JobStatus, WorkType
from app.models.user import User
from app.schemas.application import ApplicationStatusUpdateRequest
from app.schemas.job import JobStatusUpdateRequest
from app.services.job_service import resolve_job, update_job_status as _update_job_status_svc
from app.services.application_service import (
    count_by_job_and_status,
    count_by_job_grouped_by_status,
    list_by_job,
    update_application_status,
)

from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ────────────────────────────────────────────────


def _get_db() -> AsyncSession:
    """创建独立的短生命周期数据库会话。

    每次 tool 调用使用独立的 session，避免与外层 Agent
    的 checkpointer/LLM 操作共享同一个 AsyncSession 导致
    并发操作冲突 (isce 错误)。
    """
    from app.database import async_session
    # async_session() 返回一个新的 AsyncSession 实例，
    # 但需要通过 async with 管理。Tool 函数是 async 的，
    # 直接创建实例并在用完后关闭。
    return async_session()


def _get_user_id() -> str:
    """从 LangGraph config 获取当前用户 ID"""
    config = get_config()
    return str(config["configurable"]["user_id"])


# ── Filter key whitelists ──────────────────────────────────


_JOBS_FILTER_KEYS: frozenset[str] = frozenset({
    "job_code", "keyword", "status", "work_type",
    "salary_min", "salary_max",
})

_JOBS_VALID_STATUSES: frozenset[str] = frozenset({"active", "closed", "draft"})
_JOBS_VALID_WORK_TYPES: frozenset[str] = frozenset({"remote", "onsite", "hybrid"})

_APPLICATIONS_FILTER_KEYS: frozenset[str] = frozenset({
    "status", "ai_decision", "candidate_name",
    "min_ai_score", "max_ai_score",
})

_APPLICATIONS_VALID_STATUSES: frozenset[str] = frozenset({
    "pending", "interview", "rejected", "hired",
})
_APPLICATIONS_VALID_DECISIONS: frozenset[str] = frozenset({"recommend", "reject"})

_APPLICATIONS_ALLOWED_FIELDS: frozenset[str] = frozenset({
    "candidate_name", "ai_score", "ai_decision", "status",
    "ai_evaluation", "ai_decision_reason", "resume_summary",
    "cover_letter", "structured_resume",
})

_JOBS_ALLOWED_FIELDS: frozenset[str] = frozenset({
    "job_code", "title", "status", "head_count", "applications_count",
    "description", "requirements", "skills_required",
    "salary_min", "salary_max", "location", "work_type",
    "recruiter_name",
})

_APPLICATIONS_ALLOWED_GROUP_BY: frozenset[str] = frozenset({
    "status", "ai_decision",
})


def _sanitize_filter(
    raw: dict[str, Any] | None,
    allowed_keys: frozenset[str],
) -> dict[str, Any]:
    """Strip unknown keys from a filter dict."""
    if not raw:
        return {}
    return {k: v for k, v in raw.items() if k in allowed_keys}


# ── Query Tools ────────────────────────────────────────────


@tool
async def query_jobs(
    filter: dict[str, Any] | None = None,
    fields: list[str] | None = None,
    limit: int = 20,
) -> str:
    """查询岗位数据。

    filter 可包含任意组合:
      - job_code: 岗位编号（精确匹配，优先使用）
      - keyword: 关键词（模糊匹配标题）
      - status: 岗位状态 ("active", "closed", "draft")
      - work_type: 工作类型 ("remote", "onsite", "hybrid")
      - salary_min / salary_max: 薪资范围

    fields 指定返回字段，默认: ["job_code", "title", "status", "head_count", "applications_count"]
    可选字段: description, requirements, skills_required, salary_min, salary_max,
    location, work_type, recruiter_name

    只返回当前用户有权限查看的岗位（招聘者只看自己的岗位）。

    Examples:
      - 查所有活跃岗位: query_jobs(filter={"status": "active"})
      - 按编号查: query_jobs(filter={"job_code": "J04217"})
      - 模糊搜索: query_jobs(filter={"keyword": "前端"})
      - 带详情: query_jobs(filter={"job_code": "J04217"},
                   fields=["job_code","title","requirements","skills_required"])
    """
    user_id = _get_user_id()

    safe_filter = _sanitize_filter(filter, _JOBS_FILTER_KEYS)
    safe_fields = [f for f in (fields or []) if f in _JOBS_ALLOWED_FIELDS]
    if not safe_fields:
        safe_fields = ["job_code", "title", "status", "head_count", "applications_count"]

    async with _get_db() as db:
        # Base query — recruiter sees only their own jobs
        query = select(Job).where(Job.recruiter_id == uuid.UUID(user_id))

        # Apply filters
        if "job_code" in safe_filter:
            query = query.where(Job.job_code == str(safe_filter["job_code"]))

        if "keyword" in safe_filter:
            kw = str(safe_filter["keyword"]).lower().replace("%", "\\%").replace("_", "\\_")
            query = query.where(func.lower(Job.title).ilike(f"%{kw}%", escape="\\"))

        if "status" in safe_filter:
            status_val = str(safe_filter["status"]).lower()
            if status_val in _JOBS_VALID_STATUSES:
                query = query.where(Job.status == JobStatus(status_val))

        if "work_type" in safe_filter:
            wt_val = str(safe_filter["work_type"]).lower()
            if wt_val in _JOBS_VALID_WORK_TYPES:
                query = query.where(Job.work_type == WorkType(wt_val))

        if "salary_min" in safe_filter:
            try:
                sal_min = int(safe_filter["salary_min"])
                query = query.where(Job.salary_max >= sal_min)
            except (ValueError, TypeError):
                pass

        if "salary_max" in safe_filter:
            try:
                sal_max = int(safe_filter["salary_max"])
                query = query.where(Job.salary_min <= sal_max)
            except (ValueError, TypeError):
                pass

        query = query.order_by(Job.created_at.desc()).limit(min(limit, 50))
        result = await db.execute(query.options(selectinload(Job.applications), selectinload(Job.recruiter)))
        jobs = list(result.scalars().all())

        if not jobs:
            return "未找到匹配的岗位。"

        # Format output
        lines: list[str] = []
        for j in jobs:
            app_count = len(j.applications) if j.applications else 0
            item: dict[str, Any] = {"job_code": j.job_code, "title": j.title}

            for f in safe_fields:
                if f == "job_code" or f == "title":
                    continue  # already included
                if f == "status":
                    item["status"] = j.status.value
                elif f == "head_count":
                    item["head_count"] = j.head_count
                elif f == "applications_count":
                    item["applications_count"] = app_count
                elif f == "description":
                    item["description"] = j.description[:200] + "..." if len(j.description) > 200 else j.description
                elif f == "requirements":
                    item["requirements"] = j.requirements[:200] + "..." if len(j.requirements) > 200 else j.requirements
                elif f == "skills_required":
                    item["skills_required"] = j.skills_required or []
                elif f == "salary_min" and j.salary_min is not None:
                    item["salary_min"] = j.salary_min
                elif f == "salary_max" and j.salary_max is not None:
                    item["salary_max"] = j.salary_max
                elif f == "location" and j.location is not None:
                    item["location"] = j.location
                elif f == "work_type":
                    item["work_type"] = j.work_type.value
                elif f == "recruiter_name":
                    item["recruiter_name"] = j.recruiter.name if j.recruiter else None

            lines.append(str(item))

        return "\n".join(lines)


@tool
async def query_applications(
    job_code: str | None = None,
    job_title: str | None = None,
    filter: dict[str, Any] | None = None,
    fields: list[str] | None = None,
    group_by: list[str] | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    limit: int = 50,
) -> str:
    """查询投递/候选人数据。

    必须指定岗位（job_code 或 job_title）。

    filter 可包含:
      - status: 投递状态 ("pending", "interview", "rejected", "hired")
      - ai_decision: AI 决策 ("recommend", "reject")
      - candidate_name: 候选人姓名（模糊匹配）
      - min_ai_score / max_ai_score: AI 评分范围

    fields 指定返回字段，默认: ["candidate_name", "ai_score", "ai_decision", "status"]
    可选字段: ai_evaluation, ai_decision_reason, resume_summary,
    cover_letter, structured_resume

    group_by: 按字段分组统计人数
      - ["status"]: 各投递状态人数（招聘漏斗）
      - ["ai_decision"]: 各 AI 决策人数
      - ["status", "ai_decision"]: 交叉分组

    sort_by: 排序字段，默认 "ai_score"
    sort_order: "desc" 或 "asc"

    只返回当前用户有权限查看的投递数据。

    Examples:
      - 漏斗概览: query_applications(job_code="J04217", group_by=["status"])
      - 推荐候选人 Top5: query_applications(job_code="J04217",
          filter={"ai_decision": "recommend"},
          sort_by="ai_score", limit=5)
      - 被拒高分: query_applications(job_code="J04217",
          filter={"ai_decision": "reject", "min_ai_score": 70},
          sort_by="ai_score")
      - 某人评估详情: query_applications(job_code="J04217",
          filter={"candidate_name": "张三"},
          fields=["ai_score", "ai_evaluation", "ai_decision_reason"])
      - 查所有候选人: query_applications(job_code="J04217")
      - 查所有候选人(无过滤): query_applications(job_code="J04217", filter={})
    """
    user_id = _get_user_id()

    safe_filter = _sanitize_filter(filter, _APPLICATIONS_FILTER_KEYS)
    safe_fields = [f for f in (fields or []) if f in _APPLICATIONS_ALLOWED_FIELDS]
    if not safe_fields:
        safe_fields = ["candidate_name", "ai_score", "ai_decision", "status"]

    safe_group_by = [g for g in (group_by or []) if g in _APPLICATIONS_ALLOWED_GROUP_BY]

    async with _get_db() as db:
        # Resolve job
        resolved = await resolve_job(db, user_id, job_code=job_code, job_title_keyword=job_title)

        if resolved is None:
            return "未找到匹配的岗位。"
        if isinstance(resolved, list):
            job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
            return f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"

        job = resolved

        # ── group_by path ───────────────────────────────────
        lines: list[str] = []
        if safe_group_by:
            if safe_group_by == ["status"]:
                grouped = await count_by_job_grouped_by_status(db, str(job.id))
                total = sum(grouped.values())
                lines = [f"岗位「{job.title}」({job.job_code}) 共 {total} 份投递："]
                for status_key in ["pending", "interview", "rejected", "hired"]:
                    count = grouped.get(status_key, 0)
                    pct = round(count / total * 100, 1) if total > 0 else 0
                    labels = {"pending": "待审核", "interview": "面试中", "rejected": "已拒绝", "hired": "已录用"}
                    lines.append(f"  {labels.get(status_key, status_key)}: {count}人（{pct}%）")
                return "\n".join(lines)

            elif safe_group_by == ["ai_decision"]:
                stmt = (
                    select(Application.ai_decision, func.count())
                    .where(Application.job_id == job.id)
                    .group_by(Application.ai_decision)
                )
                rows = (await db.execute(stmt)).all()
                lines = [f"岗位「{job.title}」({job.job_code}) AI 决策分布："]
                for decision_val, count in rows:
                    label = {"recommend": "推荐", "reject": "不推荐"}.get(str(decision_val), str(decision_val))
                    lines.append(f"  {label}: {count}人")
                return "\n".join(lines)

            elif set(safe_group_by) == {"status", "ai_decision"}:
                cross_stmt = (
                    select(Application.status, Application.ai_decision, func.count())
                    .where(Application.job_id == job.id)
                    .group_by(Application.status, Application.ai_decision)
                )
                cross_rows = (await db.execute(cross_stmt)).all()
                lines = [f"岗位「{job.title}」({job.job_code}) 状态×决策交叉分布："]
                for status_val, decision_val, count in cross_rows:
                    s_label = {"pending": "待审核", "interview": "面试中", "rejected": "已拒绝", "hired": "已录用"}.get(status_val.value, status_val.value)
                    d_label = {"recommend": "推荐", "reject": "不推荐"}.get(str(decision_val), str(decision_val))
                    lines.append(f"  {s_label} & {d_label}: {count}人")
                return "\n".join(lines)

        # ── detail query path ───────────────────────────────
        query = (
            select(Application)
            .where(Application.job_id == job.id)
            .options(selectinload(Application.applicant))
        )

        # Apply filters
        if "status" in safe_filter:
            status_val = str(safe_filter["status"]).lower()
            if status_val in _APPLICATIONS_VALID_STATUSES:
                query = query.where(Application.status == ApplicationStatus(status_val))

        if "ai_decision" in safe_filter:
            decision_val = str(safe_filter["ai_decision"]).lower()
            if decision_val in _APPLICATIONS_VALID_DECISIONS:
                query = query.where(Application.ai_decision == decision_val)

        if "candidate_name" in safe_filter:
            name = str(safe_filter["candidate_name"]).lower().replace("%", "\\%").replace("_", "\\_")
            query = query.join(User, Application.applicant_id == User.id).where(
                func.lower(User.name).ilike(f"%{name}%", escape="\\")
            )

        if "min_ai_score" in safe_filter:
            try:
                query = query.where(Application.ai_score >= float(safe_filter["min_ai_score"]))
            except (ValueError, TypeError):
                pass

        if "max_ai_score" in safe_filter:
            try:
                query = query.where(Application.ai_score <= float(safe_filter["max_ai_score"]))
            except (ValueError, TypeError):
                pass

        # Sort
        sort_field = sort_by or "ai_score"
        if sort_field == "ai_score":
            if sort_order.lower() == "asc":
                query = query.order_by(Application.ai_score.asc().nullslast())
            else:
                query = query.order_by(Application.ai_score.desc().nullslast())
            # Secondary sort: stable order for equal/NULL ai_score
            query = query.order_by(Application.created_at.desc())
        else:
            query = query.order_by(Application.created_at.desc())

        query = query.limit(min(limit, 100))
        result = await db.execute(query)
        apps = list(result.scalars().all())

        if not apps:
            return f"岗位「{job.title}」({job.job_code}) 暂无匹配的投递记录。"

        # Format output
        lines = []
        for app in apps:
            name = app.applicant.name if app.applicant else "未知"
            item: dict[str, Any] = {"candidate_name": name}

            for f in safe_fields:
                if f == "candidate_name":
                    continue
                if f == "ai_score":
                    item["ai_score"] = app.ai_score
                elif f == "ai_decision":
                    item["ai_decision"] = app.ai_decision
                elif f == "status":
                    item["status"] = app.status.value
                elif f == "ai_evaluation" and app.ai_evaluation is not None:
                    eval_str = str(app.ai_evaluation)
                    item["ai_evaluation"] = eval_str[:300] + "..." if len(eval_str) > 300 else eval_str
                elif f == "ai_decision_reason" and app.ai_decision_reason is not None:
                    item["ai_decision_reason"] = app.ai_decision_reason
                elif f == "resume_summary" and app.structured_resume is not None:
                    # Extract a brief summary from structured_resume
                    sr = app.structured_resume
                    if isinstance(sr, dict):
                        item["resume_summary"] = f"{sr.get('name', '')}, {sr.get('work_experience_years', '?')}年经验"
                elif f == "cover_letter" and app.cover_letter is not None:
                    item["cover_letter"] = app.cover_letter[:200] + "..." if len(app.cover_letter) > 200 else app.cover_letter
                elif f == "structured_resume" and app.structured_resume is not None:
                    item["structured_resume"] = "(available)"

            lines.append(str(item))

        return "\n".join(lines)


@tool
async def query_evaluation(
    job_code: str | None = None,
    task_id: str | None = None,
) -> str:
    """查询评估任务的状态和结果。

    可通过 task_id 直接查询，或通过 job_code 查找岗位最近的评估任务。
    返回: 任务状态、进度(evaluated_count/total_count)、评估摘要
    (推荐/拒绝人数、截止分数、边界调整等)。

    只返回当前用户有权限查看的评估任务。
    """
    user_id = _get_user_id()

    async with _get_db() as db:
        task: EvaluationTask | None = None

        # Priority 1: task_id exact match
        if task_id:
            task = await db.get(EvaluationTask, uuid.UUID(task_id))
            if task and str(task.triggered_by) != user_id:
                return "无权查看此评估任务。"

        # Priority 2: find by job_code
        if not task and job_code:
            resolved = await resolve_job(db, user_id, job_code=job_code)
            if resolved is None:
                return "未找到匹配的岗位。"
            if isinstance(resolved, list):
                return "找到多个匹配的岗位，请指定岗位编号。"
            job = resolved

            stmt = (
                select(EvaluationTask)
                .where(EvaluationTask.job_id == job.id)
                .order_by(EvaluationTask.created_at.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            task = result.scalar_one_or_none()

        if not task:
            return "未找到评估任务。"

        # Build summary
        status_label = {
            EvalTaskStatus.PENDING: "等待中",
            EvalTaskStatus.RUNNING: "运行中",
            EvalTaskStatus.COMPLETED: "已完成",
            EvalTaskStatus.CONFIRMED: "已确认",
            EvalTaskStatus.FAILED: "失败",
        }.get(task.status, task.status.value)

        lines = [
            f"评估任务 {task.id}:",
            f"  状态: {status_label}",
            f"  进度: {task.evaluated_count}/{task.total_count}",
        ]

        if task.result_summary:
            summary = task.result_summary if isinstance(task.result_summary, dict) else {}
            if "recommend_count" in summary:
                lines.append(f"  推荐: {summary['recommend_count']}人")
            if "reject_count" in summary:
                lines.append(f"  不推荐: {summary['reject_count']}人")
            if "cutoff_score" in summary:
                lines.append(f"  截止分数: {summary['cutoff_score']}")

            # Per-candidate evaluation details
            evaluation_details = summary.get("evaluation_details", [])
            if evaluation_details:
                lines.append("  候选人评估详情:")
                for detail in evaluation_details:
                    name = detail.get("applicant_name") or "未知"
                    score = detail.get("ai_score")
                    decision = detail.get("ai_decision", "")
                    reason = detail.get("ai_decision_reason", "")
                    decision_label = "推荐" if decision == "recommend" else "不推荐"
                    score_str = f"{score}分" if score is not None else "未知"
                    lines.append(f"    - {name}: {score_str} ({decision_label}) {reason}")

        if task.error_message:
            lines.append(f"  错误: {task.error_message}")

        return "\n".join(lines)


# ── Write Tools ────────────────────────────────────────────


@tool
async def trigger_evaluation(
    job_code: str | None = None,
    job_title: str | None = None,
) -> str:
    """对岗位触发 AI 简历评估。

    评估过程可能需要数分钟，会实时报告进度。
    评估完成后候选人获得 AI 评分和推荐/拒绝决策，
    但不会自动变更状态——需调用 confirm_evaluation 确认。

    ⚠️ 评估是耗时操作，触发前应确认用户意图。

    Args:
        job_code: 岗位编号（优先使用）
        job_title: 岗位名称（模糊匹配，job_code 优先）
    """
    user_id = _get_user_id()
    job_id: uuid.UUID | None = None
    job_title_cache: str = ""

    # Phase 1: Resolve job & create task record (own session)
    async with _get_db() as db:
        # Resolve job
        resolved = await resolve_job(db, user_id, job_code=job_code, job_title_keyword=job_title)

        if resolved is None:
            return "未找到匹配的岗位。"
        if isinstance(resolved, list):
            job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
            return f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"

        job = resolved
        job_id = job.id
        job_title_cache = job.title

        # Concurrency check
        existing_stmt = select(EvaluationTask).where(
            EvaluationTask.job_id == job.id,
            EvaluationTask.status.in_([EvalTaskStatus.PENDING, EvalTaskStatus.RUNNING]),
        )
        existing_task = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing_task:
            return (
                f"⚠️ 岗位「{job.title}」已有正在进行的评估任务 "
                f"(task_id={existing_task.id}, status={existing_task.status.value})。"
            )

        # Count pending applications
        count_stmt = select(func.count()).select_from(Application).where(
            Application.job_id == job.id,
            Application.status == ApplicationStatus.PENDING,
        )
        pending_count: int = (await db.execute(count_stmt)).scalar() or 0

        if pending_count == 0:
            return f"岗位「{job.title}」暂无待处理的简历，无法触发评估。"

        # Create evaluation task record
        task_id = uuid.uuid4()
        eval_task = EvaluationTask(
            id=task_id,
            job_id=job.id,
            triggered_by=uuid.UUID(user_id),
            status=EvalTaskStatus.PENDING,
            total_count=pending_count,
        )
        db.add(eval_task)
        await db.commit()

    task_id_str = str(task_id)

    # Phase 2: Run evaluation graph (no shared db — graph manages its own sessions)
    await adispatch_custom_event("progress", {
        "status": f"正在评估「{job_title_cache}」岗位的简历...",
        "total_count": pending_count,
    })

    from app.database import get_checkpointer
    from app.services.agent.graph import build_evaluation_graph
    from app.services.agent.state import EvaluationState

    checkpointer = get_checkpointer()
    graph = build_evaluation_graph(checkpointer)

    initial_state: EvaluationState = {
        "job_id": str(job_id),
        "triggered_by": user_id,
        "task_id": task_id_str,
        "errors": [],
    }

    eval_config: RunnableConfig = {
        "configurable": {
            "thread_id": task_id_str,
        }
    }

    try:
        async for event in graph.astream_events(initial_state, config=eval_config, version="v2"):
            if event.get("event") == "on_custom_event":
                event_data = event.get("data", {})
                await adispatch_custom_event("progress", event_data)
    except Exception as exc:
        async with _get_db() as err_db:
            failed_task = await err_db.get(EvaluationTask, task_id)
            if failed_task and failed_task.status not in (
                EvalTaskStatus.COMPLETED, EvalTaskStatus.CONFIRMED, EvalTaskStatus.FAILED,
            ):
                failed_task.status = EvalTaskStatus.FAILED
                failed_task.error_message = f"评估工作流异常: {exc}"
                await err_db.commit()
        return f"❌ 评估工作流执行出错：{exc}"

    async with _get_db() as db:
        final_task = await db.get(EvaluationTask, task_id)
        if final_task and final_task.status == EvalTaskStatus.COMPLETED:
            summary = final_task.result_summary or {}
            recommend_count = summary.get("recommend_count", 0)
            reject_count = summary.get("reject_count", 0)
            cutoff_score = summary.get("cutoff_score", 0)
            evaluation_details = summary.get("evaluation_details", [])

            lines = [
                f"✅ 岗位「{job_title_cache}」评估完成！",
                f"共 {final_task.total_count} 份简历，推荐 {recommend_count} 人，不推荐 {reject_count} 人。",
                f"截止分数: {cutoff_score}",
            ]

            # Per-candidate evaluation details
            if evaluation_details:
                lines.append("")
                for detail in evaluation_details:
                    name = detail.get("applicant_name") or "未知"
                    score = detail.get("ai_score")
                    decision = detail.get("ai_decision", "")
                    reason = detail.get("ai_decision_reason", "")
                    decision_label = "推荐" if decision == "recommend" else "不推荐"
                    score_str = f"{score}分" if score is not None else "未知"
                    lines.append(f"  - {name}: {score_str} ({decision_label}) {reason}")

            lines.append("")
            lines.append(f"任务 ID: {task_id_str}")
            lines.append("需调用 confirm_evaluation 确认结果后才会变更候选人状态。")

            return "\n".join(lines)

    return f"评估任务 {task_id_str} 状态异常，请查看详情。"


@tool
async def confirm_evaluation(
    task_id: str,
) -> str:
    """确认评估结果，按 AI 建议批量更新候选人状态。

    评估完成后需确认才会实际变更候选人状态
    (pending → interview 或 rejected)。

    ⚠️ 写操作，执行前必须向用户确认！

    Args:
        task_id: 评估任务 ID
    """
    user_id = _get_user_id()

    async with _get_db() as db:
        task = await db.get(EvaluationTask, uuid.UUID(task_id))
        if not task:
            return "评估任务不存在。"
        if str(task.triggered_by) != user_id:
            return "无权操作此评估任务。"
        if task.status != EvalTaskStatus.COMPLETED:
            return f"任务状态为 {task.status.value}，只有 completed 状态才可确认。"

        # Batch update: recommend → interview, reject → rejected
        user = await db.get(User, uuid.UUID(user_id))
        if user is None:
            return "用户不存在。"

        updated_count = 0

        # Recommend → interview
        recommend_stmt = select(Application).where(
            Application.job_id == task.job_id,
            Application.ai_decision == "recommend",
            Application.status == ApplicationStatus.PENDING,
        )
        recommend_apps = list((await db.execute(recommend_stmt)).scalars().all())
        for app in recommend_apps:
            app.status = ApplicationStatus.INTERVIEW
            updated_count += 1

        # Reject → rejected
        reject_stmt = select(Application).where(
            Application.job_id == task.job_id,
            Application.ai_decision == "reject",
            Application.status == ApplicationStatus.PENDING,
        )
        reject_apps = list((await db.execute(reject_stmt)).scalars().all())
        for app in reject_apps:
            app.status = ApplicationStatus.REJECTED
            updated_count += 1

        task.status = EvalTaskStatus.CONFIRMED
        await db.commit()

        return f"✅ 已确认评估结果，更新了 {updated_count} 位候选人的状态。"


@tool
async def update_candidate_status(
    job_code: str,
    candidate_name: str,
    target_status: str,
) -> str:
    """变更候选人状态（推进面试/拒绝等）。

    ⚠️ 写操作，执行前必须向用户确认！

    Args:
        job_code: 岗位编号
        candidate_name: 候选人姓名
        target_status: 目标状态，"interview" 或 "rejected"
    """
    user_id = _get_user_id()

    if target_status not in ("interview", "rejected"):
        return "target_status 只接受 'interview' 或 'rejected'。"

    async with _get_db() as db:
        # Resolve job
        resolved = await resolve_job(db, user_id, job_code=job_code)
        if resolved is None:
            return "未找到匹配的岗位。"
        if isinstance(resolved, list):
            return "找到多个匹配的岗位，请指定唯一岗位编号。"

        job = resolved

        # Find application by candidate name
        escaped_name = candidate_name.lower().replace("%", "\\%").replace("_", "\\_")
        name_stmt = select(Application).join(
            User, Application.applicant_id == User.id
        ).where(
            Application.job_id == job.id,
            func.lower(User.name).ilike(f"%{escaped_name}%", escape="\\"),
        ).options(selectinload(Application.applicant))
        app_result = await db.execute(name_stmt)
        apps = list(app_result.scalars().all())

        if len(apps) == 0:
            return f"未找到候选人「{candidate_name}」的申请记录。"
        if len(apps) > 1:
            return f"找到 {len(apps)} 位名为「{candidate_name}」的候选人，请提供更精确的信息。"

        app = apps[0]
        user = await db.get(User, uuid.UUID(user_id))
        if user is None:
            return "用户不存在。"

        try:
            status_enum = ApplicationStatus(target_status)
            data = ApplicationStatusUpdateRequest(status=status_enum)
            await update_application_status(db, str(app.id), data, user)
        except Exception as exc:
            return f"状态变更失败：{exc}"

        status_labels = {"interview": "面试阶段", "rejected": "已拒绝"}
        label = status_labels.get(target_status, target_status)
        name = app.applicant.name if app.applicant else candidate_name
        return f"✅ 已将候选人「{name}」推进到{label}。"


@tool
async def update_job_status(
    job_code: str,
    target_status: str,
) -> str:
    """变更岗位状态（开启/关闭等）。

    ⚠️ 写操作，执行前必须向用户确认！

    Args:
        job_code: 岗位编号
        target_status: 目标状态，"active" 或 "closed"
    """
    user_id = _get_user_id()

    if target_status not in ("active", "closed"):
        return "target_status 只接受 'active' 或 'closed'。"

    async with _get_db() as db:
        resolved = await resolve_job(db, user_id, job_code=job_code)
        if resolved is None:
            return "未找到匹配的岗位。"
        if isinstance(resolved, list):
            return "找到多个匹配的岗位，请指定唯一岗位编号。"

        job = resolved
        user = await db.get(User, uuid.UUID(user_id))
        if user is None:
            return "用户不存在。"

        try:
            status_enum = JobStatus(target_status)
            data = JobStatusUpdateRequest(status=status_enum)
            await _update_job_status_svc(db, str(job.id), data, user)
        except Exception as exc:
            return f"岗位状态变更失败：{exc}"

        action_labels = {"active": "开启", "closed": "关闭"}
        label = action_labels.get(target_status, target_status)
        return f"✅ 已{label}岗位「{job.title}」({job.job_code})。"
