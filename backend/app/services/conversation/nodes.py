"""DEPRECATED: 14-node 对话图已迁移至 ReAct Agent 架构。

原 nodes.py 中的所有节点（intent_node, dispatch_node, feedback_node 等）
已被 create_react_agent + 7 Tools 替代。详见:
  - tools.py — 7 个 Tool 定义
  - graph.py — create_react_agent 构建逻辑
  - prompts.py — HR_AGENT_SYSTEM_PROMPT + build_state_modifier

此文件将在所有引用清理后删除。
"""
