"""HR Agent ReAct 对话 — 状态辅助类型

create_react_agent 内部管理 messages 列表状态。
此模块仅定义 context injection 所需的辅助类型。
"""

from typing import Any, TypedDict


class ConversationContext(TypedDict, total=False):
    """传递给 build_state_modifier 的上下文数据。

    这些字段来自 Conversation SQL 表，在 graph 调用时
    注入到 state_modifier 中，而非作为 graph state 的一部分。
    """

    session_summary: str | None
    context_entities: dict[str, Any]
