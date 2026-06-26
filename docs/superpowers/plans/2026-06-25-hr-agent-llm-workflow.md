# HR Agent Phase 1 — LLM Provider & Workflow Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the LLM abstraction layer (DeepSeek provider) and the LangGraph evaluation workflow (collect → evaluate → screen → review → save_draft), plus the AgentService that orchestrates trigger/query/confirm.

**Architecture:** Provider pattern with `BaseLLMProvider` interface and `DeepSeekProvider` implementation. LangGraph `StateGraph` with 5 nodes processing `EvaluationState`. `AgentService` handles the async lifecycle: spawn background task, track progress, and confirm results.

**Tech Stack:** LangGraph, langchain-core, httpx (already installed), Pydantic v2, asyncio

**Prerequisite:** Plan 1 (Data & Config Foundation) must be completed first — this plan depends on its models, schemas, and config fields.

## Global Constraints

- Python 3.12 with strict type hints (`mypy --strict` must pass)
- SQLAlchemy 2.0 type-annotated style
- Pydantic v2 exclusively for validation / DTOs
- All new files go under `backend/app/`
- No placeholder code — every step has complete, runnable content
- LLM API key must not be hardcoded — read from `Settings`
- Async-first: all LLM calls and DB operations use `async/await`

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `backend/app/llm/__init__.py` | Package init | Create |
| `backend/app/llm/base.py` | BaseLLMProvider abstract class | Create |
| `backend/app/llm/schemas.py` | LLM output Pydantic schemas (re-export from agent schemas) | Create |
| `backend/app/llm/deepseek.py` | DeepSeekProvider implementation | Create |
| `backend/app/services/agent/__init__.py` | Agent module package | Create |
| `backend/app/services/agent/state.py` | EvaluationState TypedDict | Create |
| `backend/app/services/agent/prompts.py` | LLM prompt templates | Create |
| `backend/app/services/agent/nodes.py` | LangGraph node functions | Create |
| `backend/app/services/agent/graph.py` | LangGraph graph definition | Create |
| `backend/app/services/agent_service.py` | AgentService: trigger/query/confirm | Create |
| `backend/app/services/__init__.py` | Service exports | Modify |
| `backend/requirements.txt` | Add langgraph, langchain-core | Modify |

---

### Task 1: Install LangGraph Dependencies

**Files:**
- Modify: `backend/requirements.txt`

**Interfaces:**
- Produces: `langgraph` and `langchain-core` packages available for import

- [ ] **Step 1: Add dependencies to requirements.txt**

In `backend/requirements.txt`, add after the existing `httpx` line:

```
# Workflow
langgraph
langchain-core
```

- [ ] **Step 2: Install the new dependencies**

Run: `cd backend && uv pip install -r requirements.txt`

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add langgraph and langchain-core dependencies"
```

---

### Task 2: Create LLM Package — Base Provider & Schemas

**Files:**
- Create: `backend/app/llm/__init__.py`
- Create: `backend/app/llm/base.py`
- Create: `backend/app/llm/schemas.py`

**Interfaces:**
- Produces: `BaseLLMProvider` abstract class with `evaluate_resume()` and `review_borderline()` methods
- Produces: Re-exports of `DimensionScore`, `ResumeEvaluation`, `BorderlineReview` from `app.schemas.agent`

- [ ] **Step 1: Create `llm/__init__.py`**

Create `backend/app/llm/__init__.py`:

```python
from app.llm.base import BaseLLMProvider

__all__ = ["BaseLLMProvider"]
```

- [ ] **Step 2: Create `llm/base.py`**

Create `backend/app/llm/base.py`:

```python
from abc import ABC, abstractmethod

from app.schemas.agent import BorderlineReview, ResumeEvaluation


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
```

- [ ] **Step 3: Create `llm/schemas.py`**

Create `backend/app/llm/schemas.py`:

```python
"""LLM 输出结构化 Schema — 从 app.schemas.agent 重新导出，供 LLM 模块内部使用。"""

from app.schemas.agent import BorderlineReview, DimensionScore, ResumeEvaluation

__all__ = ["DimensionScore", "ResumeEvaluation", "BorderlineReview"]
```

- [ ] **Step 4: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/llm/`
Expected: SUCCESS

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/
git commit -m "feat: add BaseLLMProvider abstract class and LLM schemas"
```

---

### Task 3: Create DeepSeek Provider

**Files:**
- Create: `backend/app/llm/deepseek.py`

**Interfaces:**
- Consumes: `BaseLLMProvider` (from Task 2), `Settings.DEEPSEEK_API_KEY`, `Settings.DEEPSEEK_BASE_URL`, `Settings.DEEPSEEK_MODEL`
- Consumes: `ResumeEvaluation`, `BorderlineReview` schemas
- Produces: `DeepSeekProvider` class with `evaluate_resume()` and `review_borderline()` implementations

- [ ] **Step 1: Create `llm/deepseek.py`**

Create `backend/app/llm/deepseek.py`:

```python
import json
import asyncio
from typing import Any

import httpx

from app.config import settings
from app.llm.base import BaseLLMProvider
from app.schemas.agent import BorderlineReview, ResumeEvaluation


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek LLM 提供商实现"""

    def __init__(self) -> None:
        self._api_key: str = settings.DEEPSEEK_API_KEY
        self._base_url: str = settings.DEEPSEEK_BASE_URL
        self._model: str = settings.DEEPSEEK_MODEL
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        await self._client.aclose()

    async def _call_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        retries: int = 1,
    ) -> dict[str, Any]:
        """调用 DeepSeek Chat API，返回解析后的 JSON"""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = await self._client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
            except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < retries:
                    # 重试时附带格式纠正提示
                    payload["messages"].append(
                        {
                            "role": "assistant",
                            "content": "格式错误，请严格按 JSON Schema 输出。",
                        }
                    )
                    await asyncio.sleep(1.0)
                continue

        raise RuntimeError(f"DeepSeek API 调用失败（已重试 {retries} 次）: {last_error}")

    async def evaluate_resume(
        self,
        job_info: dict[str, object],
        structured_resume: dict[str, object],
        dimensions: list[str],
    ) -> ResumeEvaluation:
        """评估单份简历"""
        from app.services.agent.prompts import (
            EVALUATION_SYSTEM_PROMPT,
            build_evaluation_user_prompt,
        )

        system_prompt = EVALUATION_SYSTEM_PROMPT
        user_prompt = build_evaluation_user_prompt(job_info, structured_resume, dimensions)

        raw = await self._call_chat(
            system_prompt, user_prompt, retries=settings.LLM_EVALUATION_RETRIES
        )
        return ResumeEvaluation.model_validate(raw)

    async def review_borderline(
        self,
        job_info: dict[str, object],
        borderline_recommend: list[dict[str, object]],
        borderline_reject: list[dict[str, object]],
        cutoff_score: float,
    ) -> list[BorderlineReview]:
        """复评边界候选人"""
        from app.services.agent.prompts import (
            REVIEW_SYSTEM_PROMPT,
            build_review_user_prompt,
        )

        system_prompt = REVIEW_SYSTEM_PROMPT
        user_prompt = build_review_user_prompt(
            job_info, borderline_recommend, borderline_reject, cutoff_score
        )

        raw = await self._call_chat(
            system_prompt, user_prompt, retries=settings.LLM_EVALUATION_RETRIES
        )

        # API 返回 {"reviews": [...]}
        reviews = raw.get("reviews", [])
        return [BorderlineReview.model_validate(r) for r in reviews]
```

- [ ] **Step 2: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/llm/deepseek.py`
Expected: SUCCESS

- [ ] **Step 3: Commit**

```bash
git add backend/app/llm/deepseek.py
git commit -m "feat: add DeepSeekProvider with evaluate_resume and review_borderline"
```

---

### Task 4: Create Prompt Templates

**Files:**
- Create: `backend/app/services/agent/__init__.py`
- Create: `backend/app/services/agent/prompts.py`

**Interfaces:**
- Produces: `EVALUATION_SYSTEM_PROMPT`, `REVIEW_SYSTEM_PROMPT` (string constants)
- Produces: `build_evaluation_user_prompt()`, `build_review_user_prompt()` (formatting functions)

- [ ] **Step 1: Create agent package `__init__.py`**

Create `backend/app/services/agent/__init__.py`:

```python
"""HR Agent 评估工作流模块"""
```

- [ ] **Step 2: Create `prompts.py`**

Create `backend/app/services/agent/prompts.py`:

```python
"""LLM 提示词模板"""

import json

EVALUATION_SYSTEM_PROMPT = """你是一位资深 HR 顾问，擅长技术岗位简历评估。

## 任务
根据岗位要求评估候选人简历，给出结构化评分。

## 评估维度
你必须对以下每个维度进行评分（0-100），并分配权重（权重之和必须 = 1.0）：
{dimensions_section}

## 评分基准
- 90+：极优秀，远超岗位要求
- 80-89：优秀，超出岗位要求
- 70-79：良好，基本满足岗位要求
- 60-69：一般，部分满足岗位要求但有不足
- 50-59：较弱，明显不足
- 50以下：严重不匹配

## 输出要求
严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{
  "dimensions": [
    {{
      "name": "维度名称",
      "score": 85,
      "weight": 0.35,
      "reason": "评估理由"
    }}
  ],
  "weighted_total": 79.25,
  "suggestion": "recommend 或 reject 或 neutral",
  "summary": "一句话总结该候选人的匹配情况"
}}

## 偏见抑制
- 不基于性别、年龄、婚育状态做评判
- 仅关注与岗位要求直接相关的技能、经验和学历
- 对空窗期保持客观，不预设负面判断
"""

REVIEW_SYSTEM_PROMPT = """你是一位资深 HR 顾问，正在进行边界候选人复评。

## 任务
检查进面名单中靠近分数线的候选人是否应该进面，以及淘汰名单中靠近分数线的候选人是否不该被淘汰。

## 输出要求
对每个候选人给出判断，严格按照以下 JSON 格式输出：
{{
  "reviews": [
    {{
      "application_id": "申请ID",
      "action": "keep 或 adjust",
      "new_decision": "recommend 或 reject（action=adjust 时必填，keep 时为 null）",
      "reason": "判断理由"
    }}
  ]
}}

## 判断标准
- 仅在你有明确理由认为原决策有误时才 adjust
- 如果候选人确实处于边界且差距不大，倾向于 keep（维持原决策）
- adjust 时必须给出充分的理由
"""


def build_evaluation_user_prompt(
    job_info: dict[str, object],
    structured_resume: dict[str, object],
    dimensions: list[str],
) -> str:
    """构建简历评估的用户提示词"""
    dimensions_section = "\n".join(
        f"- **{d}**" for d in dimensions
    )
    system_text = EVALUATION_SYSTEM_PROMPT.format(dimensions_section=dimensions_section)

    # 用独立的 format 避免 {{}} 转义问题
    job_json = json.dumps(job_info, ensure_ascii=False, indent=2)
    resume_json = json.dumps(structured_resume, ensure_ascii=False, indent=2)

    return f"""{system_text}

## 岗位要求
```json
{job_json}
```

## 候选人简历
```json
{resume_json}
```"""


def build_review_user_prompt(
    job_info: dict[str, object],
    borderline_recommend: list[dict[str, object]],
    borderline_reject: list[dict[str, object]],
    cutoff_score: float,
) -> str:
    """构建边界复评的用户提示词"""
    job_json = json.dumps(job_info, ensure_ascii=False, indent=2)
    recommend_json = json.dumps(borderline_recommend, ensure_ascii=False, indent=2)
    reject_json = json.dumps(borderline_reject, ensure_ascii=False, indent=2)

    return f"""{REVIEW_SYSTEM_PROMPT}

## 岗位要求
```json
{job_json}
```

## 进面分数线：{cutoff_score}

## 进面名单中的边界候选人（分数在分数线 ± 范围内）
```json
{recommend_json}
```

## 淘汰名单中的边界候选人（分数在分数线 ± 范围内）
```json
{reject_json}
```"""
```

- [ ] **Step 3: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/services/agent/prompts.py`
Expected: SUCCESS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/agent/
git commit -m "feat: add LLM prompt templates for evaluation and review"
```

---

### Task 5: Create EvaluationState

**Files:**
- Create: `backend/app/services/agent/state.py`

**Interfaces:**
- Produces: `EvaluationState` TypedDict with all fields used by graph nodes
- Later tasks consume: `state["job_id"]`, `state["applications"]`, `state["evaluation_results"]`, etc.

- [ ] **Step 1: Create `state.py`**

Create `backend/app/services/agent/state.py`:

```python
"""LangGraph 工作流状态定义"""

from typing import TypedDict


class EvaluationState(TypedDict, total=False):
    """评估工作流状态

    所有字段都是可选的（total=False），因为不同节点逐步填充状态。
    """

    # 输入
    job_id: str
    triggered_by: str
    task_id: str

    # 收集阶段产出
    job_info: dict[str, object]  # 岗位信息
    applications: list[dict[str, object]]  # 待评估的申请列表（含 structured_resume）

    # 评估阶段产出
    evaluation_results: list[dict[str, object]]  # 每份简历的评估结果
    evaluated_count: int  # 已评估数量（用于进度更新）

    # 筛选阶段产出
    screening_result: dict[str, object]  # 排序结果 + cutoff_score

    # 复评阶段产出
    review_adjustments: list[dict[str, object]]  # 边界候选人调整

    # 错误处理
    errors: list[str]  # 累积的错误信息
```

- [ ] **Step 2: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/services/agent/state.py`
Expected: SUCCESS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/agent/state.py
git commit -m "feat: add EvaluationState TypedDict for LangGraph workflow"
```

---

### Task 6: Create LangGraph Nodes

**Files:**
- Create: `backend/app/services/agent/nodes.py`

**Interfaces:**
- Consumes: `EvaluationState` (from Task 5), `BaseLLMProvider` (from Task 2), `Settings` config
- Consumes: ORM models `Application`, `Job`, `EvaluationTask`, `EvalTaskStatus` (from Plan 1)
- Produces: `collect_node`, `evaluate_node`, `screen_node`, `review_node`, `save_draft_node` — async functions that take and return `EvaluationState`

- [ ] **Step 1: Create `nodes.py`**

Create `backend/app/services/agent/nodes.py`:

```python
"""LangGraph 评估工作流节点实现"""

import asyncio
from datetime import datetime, UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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


async def collect_node(
    state: EvaluationState,
    db: AsyncSession,
) -> EvaluationState:
    """收集阶段：获取岗位下所有 pending 申请"""
    job_id = state.get("job_id", "")
    triggered_by = state.get("triggered_by", "")
    task_id = state.get("task_id", "")

    errors: list[str] = list(state.get("errors", []))

    # 更新任务状态为 running
    task = await db.get(EvaluationTask, task_id)
    if not task:
        errors.append(f"评估任务不存在: {task_id}")
        return {**state, "errors": errors}

    task.status = EvalTaskStatus.RUNNING
    await db.commit()

    # 查询岗位
    job = await db.get(Job, job_id)
    if not job:
        task.status = EvalTaskStatus.FAILED
        task.error_message = "岗位不存在"
        await db.commit()
        errors.append("岗位不存在")
        return {**state, "errors": errors}

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
        return {**state, "errors": errors}

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

    return {
        **state,
        "job_info": job_info,
        "applications": app_list,
        "errors": errors,
    }


async def evaluate_node(
    state: EvaluationState,
    db: AsyncSession,
) -> EvaluationState:
    """评估阶段：逐份评估简历（LLM × N）"""
    job_info = state.get("job_info", {})
    applications = state.get("applications", [])
    task_id = state.get("task_id", "")
    existing_errors: list[str] = list(state.get("errors", []))

    evaluation_results: list[dict[str, Any]] = list(state.get("evaluation_results", []))
    evaluated_count: int = state.get("evaluated_count", 0)
    errors: list[str] = existing_errors

    dimensions = ["技能匹配", "经验相关性", "学历达标", "综合印象"]

    provider = _get_llm_provider()
    try:
        for app_data in applications:
            app_id = app_data["application_id"]
            try:
                structured_resume = app_data.get("structured_resume")
                if not structured_resume:
                    # 如果没有结构化简历，用文本简历构造一个简单结构
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

            except Exception as exc:
                errors.append(f"评估简历失败 (application_id={app_id}): {exc}")
                evaluated_count += 1

            # 速率限制
            await asyncio.sleep(0.5)

    finally:
        await provider.close()

    # 如果所有简历都评估失败
    if not evaluation_results:
        task = await db.get(EvaluationTask, task_id)
        if task:
            task.status = EvalTaskStatus.FAILED
            task.error_message = "所有简历评估失败: " + "; ".join(errors)
            await db.commit()

    return {
        **state,
        "evaluation_results": evaluation_results,
        "evaluated_count": evaluated_count,
        "errors": errors,
    }


async def screen_node(
    state: EvaluationState,
    db: AsyncSession,
) -> EvaluationState:
    """筛选阶段：按加权总分排序，取 Top N 进面（纯排序，无 LLM）"""
    evaluation_results = list(state.get("evaluation_results", []))
    job_info = state.get("job_info", {})
    errors: list[str] = list(state.get("errors", []))

    if not evaluation_results:
        return {
            **state,
            "screening_result": {
                "recommend_list": [],
                "reject_list": [],
                "cutoff_score": 0.0,
            },
        }

    # 按加权总分降序排列
    sorted_results = sorted(
        evaluation_results,
        key=lambda x: x.get("weighted_total", 0),
        reverse=True,
    )

    # 确定 cutoff
    interview_quota = job_info.get("interview_quota")

    if interview_quota is not None:
        # 有面试人数上限：取 Top N
        quota = int(interview_quota)
        recommend_list = sorted_results[:quota]
        reject_list = sorted_results[quota:]
        cutoff_score = recommend_list[-1].get("weighted_total", 0) if recommend_list else 0.0
    else:
        # 无上限：按 60 分阈值划分
        recommend_list = [r for r in sorted_results if r.get("weighted_total", 0) >= 60]
        reject_list = [r for r in sorted_results if r.get("weighted_total", 0) < 60]
        cutoff_score = 60.0

    screening_result: dict[str, Any] = {
        "recommend_list": recommend_list,
        "reject_list": reject_list,
        "cutoff_score": cutoff_score,
    }

    return {
        **state,
        "screening_result": screening_result,
    }


async def review_node(
    state: EvaluationState,
    db: AsyncSession,
) -> EvaluationState:
    """复评阶段：LLM 复评边界候选人"""
    screening_result = state.get("screening_result", {})
    job_info = state.get("job_info", {})
    errors: list[str] = list(state.get("errors", []))

    recommend_list: list[dict[str, Any]] = screening_result.get("recommend_list", [])
    reject_list: list[dict[str, Any]] = screening_result.get("reject_list", [])
    cutoff_score: float = screening_result.get("cutoff_score", 0.0)

    borderline_range = settings.LLM_BORDERLINE_RANGE

    # 筛选边界候选人
    borderline_recommend: list[dict[str, Any]] = [
        r for r in recommend_list
        if abs(r.get("weighted_total", 0) - cutoff_score) <= borderline_range
    ]
    borderline_reject: list[dict[str, Any]] = [
        r for r in reject_list
        if abs(r.get("weighted_total", 0) - cutoff_score) <= borderline_range
    ]

    # 如果没有边界候选人，跳过复评
    if not borderline_recommend and not borderline_reject:
        return {
            **state,
            "review_adjustments": [],
        }

    # 调用 LLM 复评
    provider = _get_llm_provider()
    try:
        # 构建边界候选人的摘要信息（不传完整评估结果，控制 token）
        borderline_recommend_summary = [
            {
                "application_id": r["application_id"],
                "applicant_name": r.get("applicant_name"),
                "weighted_total": r.get("weighted_total", 0),
                "suggestion": r.get("suggestion"),
                "summary": r.get("evaluation", {}).get("summary", ""),
            }
            for r in borderline_recommend
        ]
        borderline_reject_summary = [
            {
                "application_id": r["application_id"],
                "applicant_name": r.get("applicant_name"),
                "weighted_total": r.get("weighted_total", 0),
                "suggestion": r.get("suggestion"),
                "summary": r.get("evaluation", {}).get("summary", ""),
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
        # 复评失败不重试，沿用 screen 步骤的排序结果
        errors.append(f"边界复评失败（沿用排序结果）: {exc}")
        review_adjustments = []
    finally:
        await provider.close()

    return {
        **state,
        "review_adjustments": review_adjustments,
        "errors": errors,
    }


async def save_draft_node(
    state: EvaluationState,
    db: AsyncSession,
) -> EvaluationState:
    """保存草稿阶段：写入 ai_* 草稿字段，不更新 Application.status"""
    evaluation_results = state.get("evaluation_results", [])
    screening_result = state.get("screening_result", {})
    review_adjustments = state.get("review_adjustments", [])
    task_id = state.get("task_id", "")
    errors: list[str] = list(state.get("errors", []))

    recommend_list: list[dict[str, Any]] = screening_result.get("recommend_list", [])
    reject_list: list[dict[str, Any]] = screening_result.get("reject_list", [])

    # 构建最终决策映射：application_id → decision
    decision_map: dict[str, str] = {}
    for r in recommend_list:
        decision_map[r["application_id"]] = "recommend"
    for r in reject_list:
        decision_map[r["application_id"]] = "reject"

    # 应用复评调整
    for adj in review_adjustments:
        app_id = adj.get("application_id", "")
        action = adj.get("action", "keep")
        if action == "adjust" and adj.get("new_decision"):
            decision_map[app_id] = adj["new_decision"]

    # 构建评估结果映射：application_id → evaluation_result
    eval_map: dict[str, dict[str, Any]] = {}
    for r in evaluation_results:
        eval_map[r["application_id"]] = r

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

        # 决策理由
        if decision == "recommend":
            application.ai_decision_reason = "AI 建议进入面试"
            recommend_count += 1
        else:
            application.ai_decision_reason = "AI 建议淘汰"
            reject_count += 1

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

    return {
        **state,
        "errors": errors,
    }
```

- [ ] **Step 2: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/services/agent/nodes.py`
Expected: SUCCESS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/agent/nodes.py
git commit -m "feat: add LangGraph node implementations (collect, evaluate, screen, review, save_draft)"
```

---

### Task 7: Create LangGraph Graph Definition

**Files:**
- Create: `backend/app/services/agent/graph.py`

**Interfaces:**
- Consumes: `EvaluationState` (from Task 5), node functions (from Task 6)
- Produces: `build_evaluation_graph()` — returns a compiled `StateGraph`
- Produces: `run_evaluation_workflow()` — convenience async function to execute the graph with a DB session

- [ ] **Step 1: Create `graph.py`**

Create `backend/app/services/agent/graph.py`:

```python
"""LangGraph 评估工作流图定义"""

from sqlalchemy.ext.asyncio import AsyncSession

from langgraph.graph import StateGraph, END

from app.services.agent.state import EvaluationState
from app.services.agent.nodes import (
    collect_node,
    evaluate_node,
    screen_node,
    review_node,
    save_draft_node,
)


def build_evaluation_graph() -> StateGraph:
    """构建评估工作流图

    流程：collect → evaluate → screen → review → save_draft → END
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

    return graph


async def run_evaluation_workflow(
    state: EvaluationState,
    db: AsyncSession,
) -> EvaluationState:
    """执行完整的评估工作流

    由于 LangGraph 的节点函数签名需要 db session，
    我们手动依次执行各节点（Phase 1 简化方案）。
    LangGraph checkpoint 等高级特性在 Phase 2 补充。
    """
    # collect
    state = await collect_node(state, db)

    # 如果 collect 阶段出现致命错误（没有申请），直接返回
    if not state.get("applications"):
        return state

    # evaluate
    state = await evaluate_node(state, db)

    # 如果所有评估都失败，直接返回
    if not state.get("evaluation_results"):
        return state

    # screen
    state = await screen_node(state, db)

    # review
    state = await review_node(state, db)

    # save_draft
    state = await save_draft_node(state, db)

    return state
```

- [ ] **Step 2: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/services/agent/graph.py`
Expected: SUCCESS (may have langgraph type warnings — acceptable)

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/agent/graph.py
git commit -m "feat: add LangGraph evaluation workflow graph definition"
```

---

### Task 8: Create AgentService

**Files:**
- Create: `backend/app/services/agent_service.py`
- Modify: `backend/app/services/__init__.py`

**Interfaces:**
- Consumes: `EvaluationTask`, `EvalTaskStatus` (Plan 1), `run_evaluation_workflow()` (Task 7)
- Consumes: `Application`, `ApplicationStatus`, `Job` (Plan 1)
- Produces: `trigger_evaluation()`, `get_task_status()`, `confirm_evaluation()` — async service functions

- [ ] **Step 1: Create `agent_service.py`**

Create `backend/app/services/agent_service.py`:

```python
"""Agent 业务逻辑：触发评估、查询进度、确认结果"""

import asyncio
import logging
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
from app.models.job import Job, JobStatus
from app.models.user import User, UserRole
from app.schemas.agent import (
    ConfirmDecision,
    ConfirmRequest,
    ConfirmResponse,
    EvaluateRequest,
    EvaluateResponse,
    TaskStatusResponse,
)
from app.services.agent.graph import run_evaluation_workflow
from app.services.agent.state import EvaluationState

logger = logging.getLogger(__name__)


async def trigger_evaluation(
    db: AsyncSession,
    job_id: str,
    current_user: User,
    request: EvaluateRequest,
) -> EvaluateResponse:
    """触发评估工作流"""
    # 校验角色
    if current_user.role != UserRole.RECRUITER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅招聘者可以触发评估",
        )

    # 校验岗位
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="岗位不存在",
        )
    if job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权评估此岗位",
        )
    if job.status != JobStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="岗位未处于活跃状态",
        )

    # 并发控制：检查是否有 pending/running 的任务
    existing_stmt = select(EvaluationTask).where(
        EvaluationTask.job_id == job_id,
        EvaluationTask.status.in_([EvalTaskStatus.PENDING, EvalTaskStatus.RUNNING]),
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该岗位已有正在进行的评估任务",
        )

    # 如果请求覆盖了 interview_quota，临时更新 job（不持久化）
    if request.interview_quota is not None:
        job.interview_quota = request.interview_quota

    # 统计 pending 申请数
    count_stmt = select(Application).where(
        Application.job_id == job_id,
        Application.status == ApplicationStatus.PENDING,
    )
    pending_count = len(list((await db.execute(count_stmt)).scalars().all()))

    # 创建评估任务
    task_id = uuid.uuid4()
    eval_task = EvaluationTask(
        id=task_id,
        job_id=job_id,
        triggered_by=current_user.id,
        status=EvalTaskStatus.PENDING,
        total_count=pending_count,
    )
    db.add(eval_task)
    await db.commit()
    await db.refresh(eval_task)

    # 启动后台工作流
    asyncio.create_task(
        _run_workflow_background(str(task_id), str(job_id), str(current_user.id))
    )

    return EvaluateResponse(
        task_id=str(task_id),
        status="pending",
        total_count=pending_count,
    )


async def _run_workflow_background(
    task_id: str,
    job_id: str,
    triggered_by: str,
) -> None:
    """后台执行评估工作流"""
    from app.database import async_session

    async with async_session() as db:
        try:
            initial_state: EvaluationState = {
                "job_id": job_id,
                "triggered_by": triggered_by,
                "task_id": task_id,
                "errors": [],
            }
            await run_evaluation_workflow(initial_state, db)
        except Exception as exc:
            logger.exception("评估工作流异常: task_id=%s", task_id)
            # 标记任务失败
            task = await db.get(EvaluationTask, task_id)
            if task and task.status not in (
                EvalTaskStatus.COMPLETED,
                EvalTaskStatus.CONFIRMED,
                EvalTaskStatus.FAILED,
            ):
                task.status = EvalTaskStatus.FAILED
                task.error_message = f"工作流异常: {exc}"
                await db.commit()


async def get_task_status(
    db: AsyncSession,
    task_id: str,
    current_user: User,
) -> TaskStatusResponse:
    """查询评估任务状态"""
    task = await db.get(EvaluationTask, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评估任务不存在",
        )

    # 校验权限：只有触发者可以查看
    if task.triggered_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此评估任务",
        )

    return TaskStatusResponse(
        task_id=str(task.id),
        job_id=str(task.job_id),
        status=task.status,
        total_count=task.total_count,
        evaluated_count=task.evaluated_count,
        result_summary=task.result_summary,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def confirm_evaluation(
    db: AsyncSession,
    task_id: str,
    current_user: User,
    request: ConfirmRequest,
) -> ConfirmResponse:
    """确认评估结果，更新 Application 状态"""
    # 校验任务
    task = await db.get(EvaluationTask, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评估任务不存在",
        )

    if task.triggered_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权确认此评估任务",
        )

    if task.status != EvalTaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"评估任务状态为 {task.status.value}，无法确认（需 completed）",
        )

    # 查询该岗位下有 ai_decision 的申请
    stmt = select(Application).where(
        Application.job_id == task.job_id,
        Application.ai_decision.is_not(None),
    )
    applications = list((await db.execute(stmt)).scalars().all())

    if not applications:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有可确认的评估结果",
        )

    # 构建 decision override 映射
    override_map: dict[str, str] = {}
    for d in request.decisions:
        override_map[d.application_id] = d.final_decision

    # 更新每个 Application 的状态
    updated_count = 0
    for app in applications:
        app_id_str = str(app.id)
        if app_id_str in override_map:
            # 使用人工覆盖的决策
            final_decision = override_map[app_id_str]
        else:
            # 使用 AI 建议的决策
            final_decision = app.ai_decision if app.ai_decision else "reject"

        if final_decision == "recommend" or final_decision == "interview":
            app.status = ApplicationStatus.INTERVIEW
        else:
            app.status = ApplicationStatus.REJECTED

        updated_count += 1

    # 标记任务已确认
    task.status = EvalTaskStatus.CONFIRMED
    await db.commit()

    return ConfirmResponse(
        updated_count=updated_count,
        message=f"已确认 {updated_count} 份申请的评估结果",
    )
```

- [ ] **Step 2: Update `services/__init__.py`**

In `backend/app/services/__init__.py`, add:

```python
from . import agent_service
```

Add to the `__all__` list (if it exists), or just add the import line after the existing imports.

- [ ] **Step 3: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/services/agent_service.py`
Expected: SUCCESS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/agent_service.py backend/app/services/__init__.py
git commit -m "feat: add AgentService with trigger/query/confirm logic"
```

---

## Self-Review Checklist

### Spec Coverage

| Spec Section | Covered by Task |
|-------------|----------------|
| §4.1 Graph structure (5 nodes) | Tasks 6, 7 |
| §4.2 Graph State | Task 5 |
| §4.3 Node detailed design | Task 6 |
| §5.1 Provider abstraction | Task 2 |
| §5.2 DeepSeekProvider | Task 3 |
| §5.4 Output validation & retry | Task 3 (DeepSeekProvider._call_chat) |
| §5.5 Evaluation dimensions | Task 6 (evaluate_node) |
| §5.6 Prompt design | Task 4 |
| §7.1 LLM call failure handling | Task 6 (try/except in each node) |
| §7.3 Concurrency control | Task 8 (trigger_evaluation 409 check) |
| §7.4 Data consistency | Task 6 (save_draft doesn't update status), Task 8 (confirm in transaction) |
| §7.5 Rate limiting | Task 6 (asyncio.sleep(0.5) in evaluate_node) |
| §8 Directory structure | All tasks match spec directory layout |

### Placeholder Scan

No TBD, TODO, or placeholder text found. All code is complete.

### Type Consistency

- `EvaluationState` fields match what `nodes.py` reads/writes
- `DeepSeekProvider._call_chat` returns `dict[str, Any]` which feeds into `ResumeEvaluation.model_validate()` and `BorderlineReview.model_validate()`
- `AgentService` uses `EvaluateRequest`, `EvaluateResponse`, `TaskStatusResponse`, `ConfirmRequest`, `ConfirmResponse` from Plan 1's `app.schemas.agent`
- Node functions all take `EvaluationState` + `AsyncSession` and return `EvaluationState`
- `EvalTaskStatus` values match Plan 1 enum definition
- `ApplicationStatus.INTERVIEW` and `ApplicationStatus.REJECTED` used in confirm — matches existing enum
