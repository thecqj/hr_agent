from dataclasses import dataclass
from typing import Any, AsyncGenerator


@dataclass
class _GraphState:
    values: dict[str, Any]


class PlaceholderAgentGraph:
    """占位图：保留接口形态，避免移除 AI 后出现导入错误。"""

    async def astream_events(self, initial_state: dict, config: dict | None = None, version: str = "v1") -> AsyncGenerator[dict, None]:
        message = "AI 功能暂未启用，当前返回占位结果。"
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": type("Chunk", (), {"content": message})()},
        }

    def get_state(self, config: dict | None = None) -> _GraphState:
        return _GraphState(values={"final_response": "AI 功能暂未启用，当前返回占位结果。"})


agent_graph = PlaceholderAgentGraph()
