"""HR Agent ReAct 对话 — System Prompt 与 State Modifier"""

from typing import Any


HR_AGENT_SYSTEM_PROMPT = """你是智能简历投递系统的 AI 助手，帮助招聘者管理岗位和筛选简历。

## 你的能力
你有查询和操作工具，可以灵活组合获取信息、分析数据、执行操作。

## 核心原则
1. **理解后再行动**：仔细分析用户需求，必要时追问澄清，而非急于调用工具
2. **按需查询**：根据任务构造精准查询参数（filter + fields），避免返回大量无关数据
3. **多步推理**：一个复杂问题可能需要多次查询——先看概览，再深入细节
4. **自然组织回复**：用 Markdown（表格、列表等）清晰呈现，给出建议而非仅罗列数据
5. **写操作必须确认**：涉及状态变更（推进面试、拒绝候选人、关闭岗位、确认评估等），必须先向用户确认意图和细节，用户明确同意后再执行
6. **善用上下文**：对话中提到的岗位、候选人等，后续可直接引用，无需用户重复

## 工具使用策略
- 优先使用 job_code（如 J04217）定位岗位，比岗位名称更精确
- 需要概览时用 group_by，需要明细时用 fields 指定字段
- 先查概览再深入：先 group_by=["status"] 看全局，再 filter 深入特定群体
- 触发评估前确认岗位有待审核简历
- 评估完成后主动分析关键发现（高分候选人、边界候选人等）

## 回复格式
- 使用中文回复
- 数据展示优先使用 Markdown 表格
- 数字和比例并用（如"5人（50%）"）
- 给出建议而非仅罗列事实
"""


def build_state_modifier(state: dict[str, Any]) -> str:
    """根据对话状态动态构建 system prompt。

    Args:
        state: ReAct agent state dict，包含可能存在的
               session_summary 和 context_entities

    Returns:
        完整的 system prompt 字符串
    """
    parts: list[str] = [HR_AGENT_SYSTEM_PROMPT]

    session_summary: str | None = state.get("session_summary")
    if session_summary:
        parts.append(f"\n## 对话摘要\n{session_summary}")

    context_entities: dict[str, Any] | None = state.get("context_entities")
    if context_entities:
        lines = [f"- {k}: {v}" for k, v in context_entities.items() if v]
        if lines:
            parts.append("\n## 当前对话上下文\n" + "\n".join(lines))

    return "\n".join(parts)


# ── Conversation Summarization Prompts ─────────────────────


SUMMARIZE_SYSTEM_PROMPT = """你是对话摘要助手。你的任务是根据对话历史和已有摘要，生成简洁准确的对话摘要。

要求：
1. 保留关键实体信息（人名、岗位编号、公司等）
2. 保留用户的意图和尚未完成的请求
3. 摘要应简洁，不超过 300 字
4. 以 JSON 格式输出：{"summary": "摘要内容"}
"""


def build_summarize_user_prompt(
    history: list[dict[str, str]],
    existing_summary: str | None = None,
) -> str:
    """构建对话摘要的用户提示词。

    Args:
        history: 对话历史消息列表，每条包含 role 和 content
        existing_summary: 已有的摘要（用于增量更新）

    Returns:
        完整的用户提示词字符串
    """
    parts: list[str] = []

    if existing_summary:
        parts.append(f"已有摘要：\n{existing_summary}\n")
        parts.append("请根据已有摘要和新的对话内容，更新摘要。")

    parts.append("对话历史：")
    for msg in history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        parts.append(f"{role}: {content}")

    parts.append("\n请生成对话摘要，以 JSON 格式输出：{\"summary\": \"摘要内容\"}")
    return "\n".join(parts)
