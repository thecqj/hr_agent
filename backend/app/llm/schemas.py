"""LLM 输出结构化 Schema — 从 app.schemas.agent 重新导出，供 LLM 模块内部使用。"""

from app.schemas.agent import BorderlineReview, DimensionScore, ResumeEvaluation

__all__ = ["DimensionScore", "ResumeEvaluation", "BorderlineReview"]
