"""对话 Agent 状态定义"""

from typing import Any, TypedDict


class PendingAction(TypedDict, total=False):
    """待确认操作的上下文"""

    intent: str                    # 待执行的操作意图
    params: dict[str, Any]         # 操作参数


class ConversationState(TypedDict, total=False):
    """对话工作流状态

    所有字段都是可选的（total=False），因为不同节点逐步填充状态。
    """

    # 输入
    user_message: str                              # 用户原始消息
    current_user_id: str                           # 当前招聘者 ID

    # 意图识别输出
    intent: str                                    # 14 种意图之一
    extracted_params: dict[str, Any]               # 各意图对应的参数
    clarifying_question: str | None                # unknown 意图时的追问

    # 工作流调用输出
    task_id: str | None                            # 评估任务 ID
    evaluation_status: str | None                  # 任务最终状态

    # 反馈输出
    reply_message: str                             # 给用户的文本回复
    reply_cards: list[dict[str, Any]] | None       # 结构化卡片数据
    result_page_url: str | None                    # 评估结果页面 URL

    # 操作确认
    pending_action: PendingAction | None             # 待确认操作（TypedDict 提供结构化类型安全）

    # 错误
    errors: list[str]
