"""LangGraph 评估工作流节点实现"""

import asyncio
from datetime import datetime, UTC
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from langchain_core.callbacks import adispatch_custom_event
from langgraph.config import get_config

from app.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.deepseek import DeepSeekProvider
from app.models.application import Application, ApplicationStatus
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
from app.models.job import Job
from app.schemas.agent import ResumeEvaluation
from app.services.agent.state import EvaluationState


def _get_llm_provider() -> BaseLLMProvider:
    """根据配置获取 LLM 提供商"""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "deepseek":
        return DeepSeekProvider()
    raise ValueError(f"不支持的 LLM 提供商: {provider}")


def _get_db() -> AsyncSession:
    """从 LangGraph config 获取数据库会话"""
    config = get_config()
    db: AsyncSession = config["configurable"]["db"]
    return db


async def collect_node(state: EvaluationState) -> dict[str, Any]:
    """收集阶段：获取岗位下所有 pending 申请"""
    db = _get_db()
    job_id = state.get("job_id", "")
    task_id = state.get("task_id", "")

    errors: list[str] = list(state.get("errors", []))

    await adispatch_custom_event("progress", {"status": "正在收集简历..."})

    # 更新任务状态为 running
    task = await db.get(EvaluationTask, task_id)
    if not task:
        errors.append(f"评估任务不存在: {task_id}")
        return {"errors": errors}

    task.status = EvalTaskStatus.RUNNING
    await db.commit()

    # 查询岗位
    job = await db.get(Job, job_id)
    if not job:
        task.status = EvalTaskStatus.FAILED
        task.error_message = "岗位不存在"
        await db.commit()
        errors.append("岗位不存在")
        return {"errors": errors}

    # 查询 pending 申请
    stmt = (
        select(Application)
        .where(
            Application.job_id == job_id,
            Application.status == ApplicationStatus.PENDING,
        )
        .options(selectinload(Application.applicant))
    )
    applications = list((await db.execute(stmt)).scalars().all())

    if not applications:
        task.status = EvalTaskStatus.FAILED
        task.error_message = "该岗位没有待评估的申请"
        await db.commit()
        errors.append("该岗位没有待评估的申请")
        return {"errors": errors}

    # 构建岗位信息
    job_info: dict[str, Any] = {
        "title": job.title,
        "description": job.description,
        "skills_required": job.skills_required,
        "requirements": job.requirements,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "location": job.location,
        "work_type": job.work_type.value,
    }

    # 构建申请列表
    app_list: list[dict[str, Any]] = []
    for app in applications:
        app_data: dict[str, Any] = {
            "application_id": str(app.id),
            "applicant_name": app.applicant.name if app.applicant else None,
            "resume_text": app.resume_text,
            "structured_resume": app.structured_resume,
            "cover_letter": app.cover_letter,
        }
        app_list.append(app_data)

    # 更新 total_count
    task.total_count = len(app_list)
    await db.commit()

    await adispatch_custom_event("progress", {
        "status": "简历收集完成",
        "total_count": len(app_list),
    })

    return {
        "job_info": job_info,
        "applications": app_list,
        "errors": errors,
    }


async def evaluate_node(state: EvaluationState) -> dict[str, Any]:
    """评估阶段：逐份评估简历（LLM × N）"""
    db = _get_db()
    job_info = cast(dict[str, Any], state.get("job_info", {}))
    applications = cast(list[dict[str, Any]], state.get("applications", []))
    task_id = state.get("task_id", "")
    existing_errors: list[str] = list(state.get("errors", []))

    evaluation_results: list[dict[str, Any]] = list(cast(list[dict[str, Any]], state.get("evaluation_results", [])))
    evaluated_count: int = state.get("evaluated_count", 0)
    errors: list[str] = existing_errors

    dimensions = ["技能匹配", "经验相关性", "学历达标", "综合印象"]

    await adispatch_custom_event("progress", {
        "status": "正在评估简历",
        "evaluated_count": 0,
        "total_count": len(applications),
    })

    provider: BaseLLMProvider | None = None
    try:
        provider = _get_llm_provider()
        for app_data in applications:
            app_id = app_data["application_id"]
            try:
                structured_resume = app_data.get("structured_resume")
                if not structured_resume:
                    structured_resume = {"raw_text": app_data.get("resume_text", "")}

                result: ResumeEvaluation = await provider.evaluate_resume(
                    job_info=job_info,
                    structured_resume=structured_resume,
                    dimensions=dimensions,
                )

                evaluation_results.append(
                    {
                        "application_id": app_id,
                        "applicant_name": app_data.get("applicant_name"),
                        "evaluation": result.model_dump(),
                        "weighted_total": result.weighted_total,
                        "suggestion": result.suggestion,
                    }
                )

                evaluated_count += 1

                # 更新进度
                task = await db.get(EvaluationTask, task_id)
                if task:
                    task.evaluated_count = evaluated_count
                    await db.commit()

                await adispatch_custom_event("progress", {
                    "status": "正在评估简历",
                    "evaluated_count": evaluated_count,
                    "total_count": len(applications),
                })

            except Exception as exc:
                errors.append(f"评估简历失败 (application_id={app_id}): {exc}")
                evaluated_count += 1

            # 速率限制
            await asyncio.sleep(0.5)

    finally:
        if provider is not None:
            await provider.close()

    # 如果所有简历都评估失败
    if not evaluation_results:
        task = await db.get(EvaluationTask, task_id)
        if task:
            task.status = EvalTaskStatus.FAILED
            task.error_message = "所有简历评估失败: " + "; ".join(errors)
            await db.commit()

    return {
        "evaluation_results": evaluation_results,
        "evaluated_count": evaluated_count,
        "errors": errors,
    }


async def screen_node(state: EvaluationState) -> dict[str, Any]:
    """筛选阶段：按固定阈值 60 分筛选（纯排序，无 LLM）"""
    evaluation_results = list(cast(list[dict[str, Any]], state.get("evaluation_results", [])))

    if not evaluation_results:
        return {
            "screening_result": {
                "recommend_list": [],
                "reject_list": [],
                "cutoff_score": 60.0,
            },
        }

    await adispatch_custom_event("progress", {"status": "正在筛选候选人..."})

    # 按加权总分降序排列
    sorted_results = sorted(
        evaluation_results,
        key=lambda x: float(x.get("weighted_total", 0)),
        reverse=True,
    )

    # 固定阈值：ai_score >= 60 → recommend, < 60 → reject
    cutoff_score = 60.0
    recommend_list = [r for r in sorted_results if float(r.get("weighted_total", 0)) >= cutoff_score]
    reject_list = [r for r in sorted_results if float(r.get("weighted_total", 0)) < cutoff_score]

    screening_result: dict[str, Any] = {
        "recommend_list": recommend_list,
        "reject_list": reject_list,
        "cutoff_score": cutoff_score,
    }

    return {
        "screening_result": screening_result,
    }


async def review_node(state: EvaluationState) -> dict[str, Any]:
    """复评阶段：LLM 复评边界候选人"""
    screening_result = cast(dict[str, Any], state.get("screening_result", {}))
    job_info = cast(dict[str, Any], state.get("job_info", {}))
    errors: list[str] = list(state.get("errors", []))

    recommend_list: list[dict[str, Any]] = cast(list[dict[str, Any]], screening_result.get("recommend_list", []))
    reject_list: list[dict[str, Any]] = cast(list[dict[str, Any]], screening_result.get("reject_list", []))
    cutoff_score: float = float(screening_result.get("cutoff_score", 0.0))

    borderline_range = settings.LLM_BORDERLINE_RANGE

    # 筛选边界候选人
    borderline_recommend: list[dict[str, Any]] = [
        r for r in recommend_list
        if abs(float(r.get("weighted_total", 0)) - cutoff_score) <= borderline_range
    ]
    borderline_reject: list[dict[str, Any]] = [
        r for r in reject_list
        if abs(float(r.get("weighted_total", 0)) - cutoff_score) <= borderline_range
    ]

    # 如果没有边界候选人，跳过复评
    if not borderline_recommend and not borderline_reject:
        return {
            "review_adjustments": [],
        }

    await adispatch_custom_event("progress", {"status": "正在复评边界候选人..."})

    # 调用 LLM 复评
    provider: BaseLLMProvider | None = None
    try:
        provider = _get_llm_provider()
        borderline_recommend_summary = [
            {
                "application_id": r["application_id"],
                "applicant_name": r.get("applicant_name"),
                "weighted_total": r.get("weighted_total", 0),
                "suggestion": r.get("suggestion"),
                "summary": cast(dict[str, Any], r.get("evaluation", {})).get("summary", ""),
            }
            for r in borderline_recommend
        ]
        borderline_reject_summary = [
            {
                "application_id": r["application_id"],
                "applicant_name": r.get("applicant_name"),
                "weighted_total": r.get("weighted_total", 0),
                "suggestion": r.get("suggestion"),
                "summary": cast(dict[str, Any], r.get("evaluation", {})).get("summary", ""),
            }
            for r in borderline_reject
        ]

        reviews = await provider.review_borderline(
            job_info=job_info,
            borderline_recommend=borderline_recommend_summary,
            borderline_reject=borderline_reject_summary,
            cutoff_score=cutoff_score,
        )

        review_adjustments: list[dict[str, Any]] = [
            review.model_dump() for review in reviews
        ]

    except Exception as exc:
        errors.append(f"边界复评失败（沿用排序结果）: {exc}")
        review_adjustments = []
    finally:
        if provider is not None:
            await provider.close()

    return {
        "review_adjustments": review_adjustments,
        "errors": errors,
    }


async def save_draft_node(state: EvaluationState) -> dict[str, Any]:
    """保存草稿阶段：写入 ai_* 草稿字段，不更新 Application.status"""
    db = _get_db()
    evaluation_results = cast(list[dict[str, Any]], state.get("evaluation_results", []))
    screening_result = cast(dict[str, Any], state.get("screening_result", {}))
    review_adjustments = cast(list[dict[str, Any]], state.get("review_adjustments", []))
    task_id = state.get("task_id", "")
    errors: list[str] = list(state.get("errors", []))

    recommend_list: list[dict[str, Any]] = cast(list[dict[str, Any]], screening_result.get("recommend_list", []))
    reject_list: list[dict[str, Any]] = cast(list[dict[str, Any]], screening_result.get("reject_list", []))

    # 构建最终决策映射：application_id → decision
    decision_map: dict[str, str] = {}
    for r in recommend_list:
        decision_map[str(r["application_id"])] = "recommend"
    for r in reject_list:
        decision_map[str(r["application_id"])] = "reject"

    # 应用复评调整
    adjustment_reasons: dict[str, str] = {}
    for adj in review_adjustments:
        app_id = str(adj.get("application_id", ""))
        action = adj.get("action", "keep")
        if action == "adjust" and adj.get("new_decision"):
            decision_map[app_id] = str(adj["new_decision"])
            if adj.get("reason"):
                adjustment_reasons[app_id] = str(adj["reason"])

    # 构建评估结果映射
    eval_map: dict[str, dict[str, Any]] = {}
    for r in evaluation_results:
        eval_map[str(r["application_id"])] = r

    # 写入每个 Application 的 ai_* 字段
    recommend_count = 0
    reject_count = 0
    now = datetime.now(UTC)

    for app_id, decision in decision_map.items():
        application = await db.get(Application, app_id)
        if not application:
            errors.append(f"申请不存在: {app_id}")
            continue

        eval_result = eval_map.get(app_id, {})
        evaluation_data = eval_result.get("evaluation", {})

        application.ai_score = eval_result.get("weighted_total")
        application.ai_evaluation = evaluation_data
        application.ai_decision = decision
        application.ai_evaluated_at = now

        if app_id in adjustment_reasons:
            application.ai_decision_reason = f"边界复评调整: {adjustment_reasons[app_id]}"
        else:
            evaluation_summary = evaluation_data.get("summary", "")
            application.ai_decision_reason = evaluation_summary or ("AI 建议进入面试" if decision == "recommend" else "AI 建议淘汰")

        if decision == "recommend":
            recommend_count += 1
        else:
            reject_count += 1

    # 标记评估失败的申请
    evaluated_ids = set(decision_map.keys())
    for app_data in state.get("applications", []):
        app_id = str(app_data.get("application_id", ""))
        if app_id and app_id not in evaluated_ids:
            application = await db.get(Application, app_id)
            if application:
                application.ai_decision = "error"
                application.ai_decision_reason = "简历评估失败，请重新触发评估"
                application.ai_evaluated_at = now

    # Build evaluation details for the result summary
    evaluation_details: list[dict[str, Any]] = []
    for app_id, decision in decision_map.items():
        eval_result = eval_map.get(app_id, {})
        evaluation_data = eval_result.get("evaluation", {})
        evaluation_details.append({
            "application_id": app_id,
            "applicant_name": eval_result.get("applicant_name"),
            "ai_score": eval_result.get("weighted_total"),
            "ai_evaluation": evaluation_data.get("dimensions", []),
            "ai_decision": decision,
            "ai_decision_reason": (
                f"边界复评调整: {adjustment_reasons[app_id]}"
                if app_id in adjustment_reasons
                else evaluation_data.get("summary", "") or
                    ("AI 建议进入面试" if decision == "recommend" else "AI 建议淘汰")
            ),
        })

    # 更新 evaluation_task 状态
    task = await db.get(EvaluationTask, task_id)
    if task:
        if task.status != EvalTaskStatus.FAILED:
            task.status = EvalTaskStatus.COMPLETED
        task.result_summary = {
            "recommend_count": recommend_count,
            "reject_count": reject_count,
            "cutoff_score": screening_result.get("cutoff_score", 0),
            "total_evaluated": len(evaluation_results),
            "borderline_adjustments": len(
                [a for a in review_adjustments if a.get("action") == "adjust"]
            ),
            "evaluation_details": evaluation_details,
        }
        if errors:
            task.error_message = "; ".join(errors)

    await db.commit()

    await adispatch_custom_event("progress", {"status": "评估完成"})

    return {
        "errors": errors,
    }
