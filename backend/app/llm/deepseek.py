import json
import asyncio
from typing import Any, cast

import httpx

from app.config import settings
from app.llm.base import BaseLLMProvider
from app.schemas.agent import BorderlineReview, IntentResult, ResumeEvaluation


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
                return cast(dict[str, Any], json.loads(content))
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

    async def recognize_intent(
        self,
        user_message: str,
    ) -> IntentResult:
        """识别用户消息的意图和参数"""
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
