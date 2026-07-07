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

    @abstractmethod
    async def summarize_conversation(
        self,
        history: list[dict[str, str]],
        existing_summary: str | None = None,
    ) -> str:
        """生成对话摘要

        Args:
            history: 需要压缩的对话轮次 [{role, content}]
            existing_summary: 已有摘要（合并更新）

        Returns:
            压缩后的摘要文本
        """
        ...

    @abstractmethod
    async def parse_resume(self, raw_text: str) -> dict[str, object]:
        """解析原始简历文本，返回结构化数据

        Args:
            raw_text: 原始简历文本内容

        Returns:
            结构化的简历数据字典
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭提供商资源（如 HTTP 客户端）"""
        ...
