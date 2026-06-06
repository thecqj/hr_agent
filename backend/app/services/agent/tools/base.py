from typing import Any


def register_tool(name: str, description: str, role: str, pages: list[str], args_schema=None):
    def decorator(func):
        return func

    return decorator


def load_tools_for_context(user_role: str, current_page: str) -> list[Any]:
    return []


async def execute_tool(tool_name: str, args: dict[str, Any], user_id: str) -> Any:
    return "AI 功能暂未启用，工具调用已被占位实现替代。"
