# Phase 2 Backend Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade EvaluationGraph to true LangGraph execution with Checkpoint persistence, and extend LLM Provider with intent recognition.

**Architecture:** Refactor Phase 1's manually-sequenced node calls into a properly compiled LangGraph StateGraph with AsyncPostgresSaver checkpointer. Node signatures change from `(state, db)` to `(state)` with db from `get_config()`. Add `recognize_intent()` to the LLM provider abstraction for Phase 2's conversation agent.

**Tech Stack:** LangGraph, langgraph-checkpoint-postgres, SQLAlchemy 2.0 (async), Pydantic v2, DeepSeek API

## Global Constraints

- Python 3.12 with strict type hints, `mypy --strict` must pass
- SQLAlchemy 2.0 type-annotated style (`Mapped[str] = mapped_column(...)`)
- Pydantic v2 for all DTOs
- All async functions use `async def` with proper return type hints
- Tests run with `cd backend && uv run pytest tests/ -v`
- Type check with `cd backend && uv run mypy --strict app/`
- Working directory: `/Users/bytedance/my_code/hr_agent/.claude/worktrees/phase2-impl`

---

### Task 1: Add Checkpoint Dependency + Initialize Checkpointer

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/database.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `settings.DATABASE_URL` from `app.config`
- Produces: `get_checkpointer() -> AsyncPostgresSaver` from `app.database`, FastAPI lifespan with checkpointer setup

- [ ] **Step 1: Add dependency to requirements.txt**

Add `langgraph-checkpoint-postgres` after the existing `langchain-core` line:

```
# Workflow
langgraph
langchain-core
langgraph-checkpoint-postgres
```

- [ ] **Step 2: Install the new dependency**

Run: `cd backend && source .venv/bin/activate && uv pip install -r requirements.txt`

Expected: Successfully installed langgraph-checkpoint-postgres and its dependencies

- [ ] **Step 3: Add checkpointer initialization to database.py**

Add after the existing `async_session` definition:

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# ── LangGraph Checkpointer ──────────────────────────────────

_checkpointer: AsyncPostgresSaver | None = None


async def init_checkpointer() -> AsyncPostgresSaver:
    """Initialize and return the LangGraph PostgreSQL checkpointer."""
    global _checkpointer
    # Strip SQLAlchemy driver from URL: postgresql+psycopg:// → postgresql://
    db_url = settings.DATABASE_URL.replace("+psycopg", "")
    _checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
    await _checkpointer.setup()
    return _checkpointer


def get_checkpointer() -> AsyncPostgresSaver:
    """Return the initialized checkpointer (call after init_checkpointer)."""
    if _checkpointer is None:
        raise RuntimeError("Checkpointer not initialized — call init_checkpointer() first")
    return _checkpointer
```

- [ ] **Step 4: Add lifespan to main.py for checkpointer init**

Replace the current `app = FastAPI(...)` block with a lifespan-based initialization:

```python
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings
from app.database import init_checkpointer


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    # Startup
    await init_checkpointer()
    yield
    # Shutdown (no explicit cleanup needed for checkpointer)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 统一挂载 /api 路由
app.include_router(api_router)


@app.get("/", response_model=Dict[str, Any])
async def root() -> Dict[str, Any]:
    return {
        "message": f"{settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Run existing tests to verify no regressions**

Run: `cd backend && uv run pytest tests/ -v`

Expected: 57 passed (same as baseline)

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/app/database.py backend/app/main.py
git commit -m "feat: add LangGraph AsyncPostgresSaver checkpointer initialization"
```

---

### Task 2: Refactor Evaluation Nodes for LangGraph Execution

**Files:**
- Modify: `backend/app/services/agent/nodes.py`

**Interfaces:**
- Consumes: `EvaluationState` from `app.services.agent.state`, `get_config()` from `langgraph.config`, `dispatch_custom_event` from `langgraph.config`
- Produces: Node functions with signature `async def node(state: EvaluationState) -> dict` returning partial state updates

**Key changes:**
1. Remove `db: AsyncSession` parameter from all 5 node functions
2. Get db from `get_config()["configurable"]["db"]` inside each node
3. Return partial state dicts (remove `{**state, ...}` pattern)
4. Add `dispatch_custom_event()` calls for progress reporting

- [ ] **Step 1: Add imports and update collect_node**

Replace the imports and `collect_node` function. The top of the file becomes:

```python
"""LangGraph 评估工作流节点实现"""

import asyncio
from datetime import datetime, UTC
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from langgraph.config import get_config, dispatch_custom_event

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


async def collect_node(state: EvaluationState) -> dict:
    """收集阶段：获取岗位下所有 pending 申请"""
    db = _get_db()
    job_id = state.get("job_id", "")
    task_id = state.get("task_id", "")

    errors: list[str] = list(state.get("errors", []))

    dispatch_custom_event("progress", {"status": "正在收集简历..."})

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
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "location": job.location,
        "work_type": job.work_type.value,
        "interview_quota": job.interview_quota,
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

    dispatch_custom_event("progress", {
        "status": "简历收集完成",
        "total_count": len(app_list),
    })

    return {
        "job_info": job_info,
        "applications": app_list,
        "errors": errors,
    }
```

- [ ] **Step 2: Update evaluate_node**

Replace the `evaluate_node` function:

```python
async def evaluate_node(state: EvaluationState) -> dict:
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

    dispatch_custom_event("progress", {
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

                dispatch_custom_event("progress", {
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
```

- [ ] **Step 3: Update screen_node**

Replace the `screen_node` function:

```python
async def screen_node(state: EvaluationState) -> dict:
    """筛选阶段：按加权总分排序，取 Top N 进面（纯排序，无 LLM）"""
    evaluation_results = list(cast(list[dict[str, Any]], state.get("evaluation_results", [])))
    job_info = cast(dict[str, Any], state.get("job_info", {}))

    if not evaluation_results:
        return {
            "screening_result": {
                "recommend_list": [],
                "reject_list": [],
                "cutoff_score": 0.0,
            },
        }

    dispatch_custom_event("progress", {"status": "正在筛选候选人..."})

    # 按加权总分降序排列
    sorted_results = sorted(
        evaluation_results,
        key=lambda x: float(x.get("weighted_total", 0)),
        reverse=True,
    )

    # 确定 cutoff（请求级别覆盖优先于岗位配置）
    interview_quota = state.get("interview_quota_override") or job_info.get("interview_quota")

    if interview_quota is not None:
        quota = int(interview_quota)
        recommend_list = sorted_results[:quota]
        reject_list = sorted_results[quota:]
        cutoff_score = float(recommend_list[-1].get("weighted_total", 0)) if recommend_list else 0.0
    else:
        recommend_list = [r for r in sorted_results if float(r.get("weighted_total", 0)) >= 60]
        reject_list = [r for r in sorted_results if float(r.get("weighted_total", 0)) < 60]
        cutoff_score = 60.0

    screening_result: dict[str, Any] = {
        "recommend_list": recommend_list,
        "reject_list": reject_list,
        "cutoff_score": cutoff_score,
    }

    return {
        "screening_result": screening_result,
    }
```

- [ ] **Step 4: Update review_node**

Replace the `review_node` function:

```python
async def review_node(state: EvaluationState) -> dict:
    """复评阶段：LLM 复评边界候选人"""
    db = _get_db()
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

    dispatch_custom_event("progress", {"status": "正在复评边界候选人..."})

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
```

- [ ] **Step 5: Update save_draft_node**

Replace the `save_draft_node` function:

```python
async def save_draft_node(state: EvaluationState) -> dict:
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

    # 更新 evaluation_task 状态
    task = await db.get(EvaluationTask, task_id)
    if task:
        task.status = EvalTaskStatus.COMPLETED
        task.result_summary = {
            "recommend_count": recommend_count,
            "reject_count": reject_count,
            "cutoff_score": screening_result.get("cutoff_score", 0),
            "total_evaluated": len(evaluation_results),
            "borderline_adjustments": len(
                [a for a in review_adjustments if a.get("action") == "adjust"]
            ),
        }
        if errors:
            task.error_message = "; ".join(errors)

    await db.commit()

    dispatch_custom_event("progress", {"status": "评估完成"})

    return {
        "errors": errors,
    }
```

- [ ] **Step 6: Run mypy to check type correctness**

Run: `cd backend && uv run mypy --strict app/services/agent/nodes.py`

Expected: No errors (the old `type: ignore[call-overload]` comments are no longer needed since node signatures now match LangGraph expectations)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/agent/nodes.py
git commit -m "refactor: update evaluation node signatures for LangGraph execution

- Remove db parameter from all 5 node functions
- Get db session from get_config()[\"configurable\"][\"db\"]
- Return partial state dicts instead of {**state, ...}
- Add dispatch_custom_event() calls for SSE progress reporting"
```

---

### Task 3: Upgrade Evaluation Graph + Agent Service

**Files:**
- Modify: `backend/app/services/agent/graph.py`
- Modify: `backend/app/services/agent_service.py`

**Interfaces:**
- Consumes: `get_checkpointer()` from `app.database`, updated node signatures from Task 2
- Produces: `build_evaluation_graph() -> CompiledStateGraph`, `run_evaluation_workflow()` that uses graph.astream_events

- [ ] **Step 1: Upgrade graph.py to compile with checkpointer**

Replace the entire `graph.py` content:

```python
"""LangGraph 评估工作流图定义 & 执行"""

from sqlalchemy.ext.asyncio import AsyncSession

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.services.agent.state import EvaluationState
from app.services.agent.nodes import (
    collect_node,
    evaluate_node,
    screen_node,
    review_node,
    save_draft_node,
)


def build_evaluation_graph(checkpointer: AsyncPostgresSaver) -> StateGraph:  # type: ignore[type-arg]
    """构建评估工作流图并编译

    流程：collect → evaluate → screen → review → save_draft → END

    Args:
        checkpointer: LangGraph PostgreSQL 持久化存储
    """
    graph = StateGraph(EvaluationState)

    # 添加节点
    graph.add_node("collect", collect_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("screen", screen_node)
    graph.add_node("review", review_node)
    graph.add_node("save_draft", save_draft_node)

    # 设置入口
    graph.set_entry_point("collect")

    # 定义边
    graph.add_edge("collect", "evaluate")
    graph.add_edge("evaluate", "screen")
    graph.add_edge("screen", "review")
    graph.add_edge("review", "save_draft")
    graph.add_edge("save_draft", END)

    return graph.compile(checkpointer=checkpointer)


async def run_evaluation_workflow(
    state: EvaluationState,
    db: AsyncSession,
) -> EvaluationState:
    """执行完整的评估工作流（通过 LangGraph 图引擎）

    使用 ainvoke 执行图，db session 通过 configurable 传入。
    对于需要 SSE 流式事件的场景，直接使用 build_evaluation_graph()
    配合 astream_events() 调用。
    """
    from app.database import get_checkpointer

    checkpointer = get_checkpointer()
    graph = build_evaluation_graph(checkpointer)

    config = {
        "configurable": {
            "thread_id": state.get("task_id", "default"),
            "db": db,
        }
    }

    result = await graph.ainvoke(state, config=config)

    # ainvoke 返回完整状态 dict，类型兼容 EvaluationState
    return result  # type: ignore[return-value]
```

- [ ] **Step 2: Update agent_service.py to use the new graph execution**

The `_run_workflow_background` function needs minimal changes since `run_evaluation_workflow` still works with `(state, db)` signature. But let's also update it to handle the new pattern properly.

Replace the `_run_workflow_background` function in `agent_service.py`:

```python
async def _run_workflow_background(
    task_id: str,
    job_id: str,
    triggered_by: str,
    interview_quota_override: int | None = None,
) -> None:
    """后台执行评估工作流（通过 LangGraph 图引擎）"""
    from app.database import async_session
    from app.services.agent.graph import run_evaluation_workflow

    async with async_session() as db:
        try:
            initial_state: EvaluationState = {
                "job_id": job_id,
                "triggered_by": triggered_by,
                "task_id": task_id,
                "errors": [],
                "interview_quota_override": interview_quota_override,
            }
            await run_evaluation_workflow(initial_state, db)
        except Exception as exc:
            logger.exception("评估工作流异常: task_id=%s", task_id)
            task = await db.get(EvaluationTask, task_id)
            if task and task.status not in (
                EvalTaskStatus.COMPLETED,
                EvalTaskStatus.CONFIRMED,
                EvalTaskStatus.FAILED,
            ):
                task.status = EvalTaskStatus.FAILED
                task.error_message = f"工作流异常: {exc}"
                await db.commit()
```

The rest of `agent_service.py` (trigger_evaluation, get_task_status, confirm_evaluation) remains unchanged.

- [ ] **Step 3: Run all existing tests to verify compatibility**

Run: `cd backend && uv run pytest tests/ -v`

Expected: All 57 tests should still pass. Some tests that directly call node functions with `(state, db)` signature will FAIL because nodes now take `(state)` and get db from config. This is expected — we'll update those tests in Task 5.

If node-level tests fail, that's OK for now — we fix them in Task 5. The API-level tests (test_agent_api.py) should still pass because they go through agent_service which handles the session correctly.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/agent/graph.py backend/app/services/agent_service.py
git commit -m "feat: upgrade EvaluationGraph to true LangGraph execution with checkpointer

- build_evaluation_graph() now compiles with AsyncPostgresSaver
- run_evaluation_workflow() uses graph.ainvoke() instead of manual sequencing
- _run_workflow_background() delegates session to graph via configurable"
```

---

### Task 4: Add Intent Recognition to LLM Providers

**Files:**
- Modify: `backend/app/llm/base.py`
- Modify: `backend/app/llm/deepseek.py`
- Create: `backend/app/services/conversation/prompts.py`

**Interfaces:**
- Consumes: `BaseLLMProvider._call_chat()` pattern from DeepSeekProvider
- Produces: `BaseLLMProvider.recognize_intent() -> IntentResult`, `DeepSeekProvider.recognize_intent()`, `INTENT_SYSTEM_PROMPT` + `build_intent_user_prompt()`

- [ ] **Step 1: Add IntentResult schema to app/schemas/agent.py**

Append to `backend/app/schemas/agent.py`:

```python
class IntentResult(BaseModel):
    """意图识别结果"""

    intent: Literal["evaluate", "help", "unknown"] = Field(
        ..., description="识别出的意图类型"
    )
    confidence: float = Field(
        ..., ge=0, le=1, description="置信度 0-1"
    )
    extracted_params: dict[str, Any] = Field(
        default_factory=dict,
        description="提取的参数（evaluate 时包含 job_title, interview_quota 等）",
    )
    clarifying_question: str | None = Field(
        None, description="置信度低时的追问（仅 unknown 时）"
    )
```

- [ ] **Step 2: Add recognize_intent to BaseLLMProvider**

Add the abstract method to `backend/app/llm/base.py`:

```python
from abc import ABC, abstractmethod

from app.schemas.agent import BorderlineReview, IntentResult, ResumeEvaluation


class BaseLLMProvider(ABC):
    """LLM 提供商统一接口"""

    @abstractmethod
    async def evaluate_resume(
        self,
        job_info: dict[str, object],
        structured_resume: dict[str, object],
        dimensions: list[str],
    ) -> ResumeEvaluation:
        """评估单份简历，返回结构化结果"""
        ...

    @abstractmethod
    async def review_borderline(
        self,
        job_info: dict[str, object],
        borderline_recommend: list[dict[str, object]],
        borderline_reject: list[dict[str, object]],
        cutoff_score: float,
    ) -> list[BorderlineReview]:
        """复评边界候选人"""
        ...

    @abstractmethod
    async def recognize_intent(
        self,
        user_message: str,
    ) -> IntentResult:
        """识别用户消息的意图和参数"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭提供商资源（如 HTTP 客户端）"""
        ...
```

- [ ] **Step 3: Create conversation prompts file**

Create `backend/app/services/conversation/` directory and `prompts.py`:

```python
"""对话 Agent 的 LLM 提示词模板"""

INTENT_SYSTEM_PROMPT = """你是一个 HR 招聘助手的意图识别模块。根据用户消息，判断其意图并提取参数。

支持的意图：
1. evaluate - 触发简历评估工作流
   参数：job_title (str, 岗位名称), job_id (str, 岗位ID，可选), interview_quota (int, 进面人数，可选)
2. help - 查询使用帮助
   参数：无
3. unknown - 无法识别的意图
   参数：clarifying_question (str, 追问)

规则：
- confidence 低于 0.7 时，intent 设为 unknown 并提供 clarifying_question
- 用户提到"筛选"、"评估"、"筛选简历"、"看简历"、"帮我选"等均指向 evaluate
- 用户提到"帮助"、"能做什么"、"怎么用"等均指向 help
- 如果用户指定了进面人数（如"选5个人"），提取为 interview_quota 参数
- 如果用户提到了岗位名称，提取为 job_title 参数

严格按照以下 JSON 格式输出，不要输出任何其他内容：
{
  "intent": "evaluate|help|unknown",
  "confidence": 0.0-1.0,
  "extracted_params": {},
  "clarifying_question": "..." // 仅 unknown 时提供
}"""


def build_intent_user_prompt(user_message: str) -> str:
    """构建意图识别的用户提示词"""
    return f"用户消息：{user_message}"
```

Also create `backend/app/services/conversation/__init__.py`:

```python
"""HR Agent 对话助手模块"""
```

- [ ] **Step 4: Implement recognize_intent in DeepSeekProvider**

Add the method to `backend/app/llm/deepseek.py`:

```python
async def recognize_intent(
    self,
    user_message: str,
) -> IntentResult:
    """识别用户消息的意图和参数"""
    from app.schemas.agent import IntentResult
    from app.services.conversation.prompts import (
        INTENT_SYSTEM_PROMPT,
        build_intent_user_prompt,
    )

    system_prompt = INTENT_SYSTEM_PROMPT
    user_prompt = build_intent_user_prompt(user_message)

    raw = await self._call_chat(
        system_prompt, user_prompt, retries=settings.LLM_EVALUATION_RETRIES
    )
    return IntentResult.model_validate(raw)
```

Don't forget to update the imports at the top of `deepseek.py` — the `IntentResult` import is done locally inside the method to avoid circular imports. The existing imports at the top remain:

```python
import json
import asyncio
from typing import Any, cast

import httpx

from app.config import settings
from app.llm.base import BaseLLMProvider
from app.schemas.agent import BorderlineReview, ResumeEvaluation
```

- [ ] **Step 5: Run mypy type check**

Run: `cd backend && uv run mypy --strict app/llm/ app/services/conversation/prompts.py`

Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/agent.py backend/app/llm/base.py backend/app/llm/deepseek.py backend/app/services/conversation/__init__.py backend/app/services/conversation/prompts.py
git commit -m "feat: add intent recognition to LLM providers

- Add IntentResult schema with intent/confidence/extracted_params
- Add recognize_intent() abstract method to BaseLLMProvider
- Implement recognize_intent() in DeepSeekProvider
- Add INTENT_SYSTEM_PROMPT with evaluate/help/unknown intents"
```

---

### Task 5: Update Tests for Evaluation Graph Upgrade

**Files:**
- Modify: `backend/tests/test_agent_nodes.py`
- Modify: `backend/tests/test_agent_service.py`

**Interfaces:**
- Consumes: Updated node signatures from Task 2 (nodes take `state` only, db from config)
- Produces: Passing test suite that validates the upgraded graph execution

- [ ] **Step 1: Read existing test files to understand patterns**

Run: `cat backend/tests/test_agent_nodes.py | head -80`

Review the existing test patterns and mock setup.

- [ ] **Step 2: Update test_agent_nodes.py for new node signatures**

The key change: nodes no longer accept `db` as a parameter. Instead, we mock `get_config()` to return a config with db session.

At the top of the test file, add/modify the mock:

```python
from unittest.mock import patch

# Replace all direct calls like:
#   result = await collect_node(state, db)
# With:
#   with patch("app.services.agent.nodes.get_config", return_value={"configurable": {"db": db}}):
#       result = await collect_node(state)
```

For each test function that calls a node, wrap the call in a `patch("app.services.agent.nodes.get_config", ...)` context manager.

- [ ] **Step 3: Run node tests**

Run: `cd backend && uv run pytest tests/test_agent_nodes.py -v`

Expected: All node tests pass with the new signatures

- [ ] **Step 4: Update test_agent_service.py if needed**

The service tests call `agent_service.trigger_evaluation()` etc., which internally use `_run_workflow_background`. Since `run_evaluation_workflow` now uses `graph.ainvoke()`, we may need to mock the checkpointer. Add:

```python
from unittest.mock import patch, AsyncMock

# In test fixtures or setup:
@pytest.fixture(autouse=True)
def mock_checkpointer():
    with patch("app.services.agent.graph.get_checkpointer") as mock_get:
        mock_checkpointer = AsyncMock()
        mock_get.return_value = mock_checkpointer
        yield mock_checkpointer
```

- [ ] **Step 5: Run service tests**

Run: `cd backend && uv run pytest tests/test_agent_service.py -v`

Expected: All service tests pass

- [ ] **Step 6: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`

Expected: All tests pass (57+ tests)

- [ ] **Step 7: Commit**

```bash
git add backend/tests/test_agent_nodes.py backend/tests/test_agent_service.py
git commit -m "test: update agent tests for LangGraph execution upgrade

- Mock get_config() for node unit tests
- Mock checkpointer for service tests
- All 57+ tests passing"
```

---

### Task 6: Add Intent Recognition Tests

**Files:**
- Create: `backend/tests/test_intent_recognition.py`

**Interfaces:**
- Consumes: `DeepSeekProvider.recognize_intent()`, `IntentResult` schema
- Produces: Test suite validating intent recognition accuracy

- [ ] **Step 1: Write test file**

Create `backend/tests/test_intent_recognition.py`:

```python
"""意图识别测试"""

import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.agent import IntentResult


class TestIntentResultSchema:
    """IntentResult schema 验证测试"""

    def test_evaluate_intent(self) -> None:
        result = IntentResult(
            intent="evaluate",
            confidence=0.9,
            extracted_params={"job_title": "前端开发"},
        )
        assert result.intent == "evaluate"
        assert result.confidence == 0.9
        assert result.extracted_params["job_title"] == "前端开发"

    def test_help_intent(self) -> None:
        result = IntentResult(
            intent="help",
            confidence=0.95,
            extracted_params={},
        )
        assert result.intent == "help"

    def test_unknown_intent_with_question(self) -> None:
        result = IntentResult(
            intent="unknown",
            confidence=0.3,
            extracted_params={},
            clarifying_question="请问您想执行什么操作？",
        )
        assert result.intent == "unknown"
        assert result.clarifying_question is not None

    def test_confidence_bounds(self) -> None:
        with pytest.raises(Exception):
            IntentResult(intent="evaluate", confidence=1.5, extracted_params={})
        with pytest.raises(Exception):
            IntentResult(intent="evaluate", confidence=-0.1, extracted_params={})

    def test_invalid_intent(self) -> None:
        with pytest.raises(Exception):
            IntentResult(intent="invalid", confidence=0.5, extracted_params={})


class TestIntentRecognitionProvider:
    """DeepSeekProvider.recognize_intent 集成测试（mock LLM 响应）"""

    @pytest.mark.asyncio
    async def test_recognize_evaluate_intent(self) -> None:
        """测试识别 evaluate 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "evaluate",
            "confidence": 0.92,
            "extracted_params": {"job_title": "前端开发"},
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("帮我筛选前端开发岗位的简历")
            assert result.intent == "evaluate"
            assert result.extracted_params.get("job_title") == "前端开发"
        await provider.close()

    @pytest.mark.asyncio
    async def test_recognize_evaluate_with_quota(self) -> None:
        """测试识别带进面人数的 evaluate 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "evaluate",
            "confidence": 0.88,
            "extracted_params": {"job_title": "前端", "interview_quota": 5},
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("前端岗位选5个人进面试")
            assert result.intent == "evaluate"
            assert result.extracted_params.get("interview_quota") == 5
        await provider.close()

    @pytest.mark.asyncio
    async def test_recognize_help_intent(self) -> None:
        """测试识别 help 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "help",
            "confidence": 0.95,
            "extracted_params": {},
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("你能做什么")
            assert result.intent == "help"
        await provider.close()

    @pytest.mark.asyncio
    async def test_recognize_unknown_intent(self) -> None:
        """测试识别 unknown 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "unknown",
            "confidence": 0.4,
            "extracted_params": {},
            "clarifying_question": "请问您想执行什么操作？",
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("今天天气怎么样")
            assert result.intent == "unknown"
            assert result.clarifying_question is not None
        await provider.close()
```

- [ ] **Step 2: Run the tests**

Run: `cd backend && uv run pytest tests/test_intent_recognition.py -v`

Expected: All 8 tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_intent_recognition.py
git commit -m "test: add intent recognition tests

- IntentResult schema validation tests (5)
- DeepSeekProvider.recognize_intent() mock tests (4)"
```

---

### Task 7: Final Verification + mypy

**Files:**
- No new files

- [ ] **Step 1: Run full mypy check**

Run: `cd backend && uv run mypy --strict app/`

Expected: No errors

- [ ] **Step 2: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`

Expected: All tests pass (57 original + 8 new intent recognition tests = 65+)

- [ ] **Step 3: Commit any remaining fixes if needed**

If mypy or tests revealed issues, fix and commit.

---

## Self-Review

**1. Spec coverage check:**
- ✅ EvaluationGraph upgrade to true LangGraph execution (Task 2, 3)
- ✅ Checkpoint persistence with AsyncPostgresSaver (Task 1, 3)
- ✅ Node signature adaptation for LangGraph (Task 2)
- ✅ dispatch_custom_event for SSE progress (Task 2)
- ✅ LLM Provider recognize_intent() (Task 4)
- ✅ Intent recognition prompts (Task 4)
- ✅ Tests updated for new signatures (Task 5, 6)

**2. Placeholder scan:** No TBD/TODO found. All steps have complete code.

**3. Type consistency:**
- `_get_db() -> AsyncSession` used consistently in all 5 nodes
- `IntentResult` schema matches between `app/schemas/agent.py` and provider implementations
- `dispatch_custom_event` call signatures are consistent across nodes
- `get_config()` / `get_checkpointer()` function names are consistent
