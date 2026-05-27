from typing import Dict, Any, Callable, List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel

_tool_registry: Dict[str, Dict[str, Any]] = {}

def register_tool(name: str, description: str, role: str, pages: List[str], args_schema: Optional[type[BaseModel]] = None):
    def decorator(func: Callable):
        langchain_tool = tool(name, description=description, args_schema=args_schema)(func) if args_schema else tool(func)
        _tool_registry[name] = {
            "func": func,
            "langchain_tool": langchain_tool,
            "role": role,
            "pages": pages,
        }
        return func
    return decorator

def load_tools_for_context(user_role: str, current_page: str) -> List:
    tools = []
    for info in _tool_registry.values():
        if info["role"] in (user_role, "both") and ("*" in info["pages"] or current_page in info["pages"]):
            tools.append(info["langchain_tool"])
    return tools

async def execute_tool(tool_name: str, args: Dict[str, Any], user_id: str) -> Any:
    if tool_name not in _tool_registry:
        return f"未知工具: {tool_name}"
    func = _tool_registry[tool_name]["func"]
    import inspect
    sig = inspect.signature(func)
    if "user_id" in sig.parameters:
        args = {**args, "user_id": user_id}
    if inspect.iscoroutinefunction(func):
        return await func(**args)
    else:
        return func(**args)