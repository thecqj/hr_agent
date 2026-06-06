class PlaceholderMultiAgentGraph:
    """多智能体占位图。"""

    def invoke(self, initial_state: dict):
        return {
            "scores": [],
            "recommendations": [],
            "next_action": "end",
        }

    async def ainvoke(self, initial_state: dict, config: dict | None = None):
        return self.invoke(initial_state)


multi_agent_graph = PlaceholderMultiAgentGraph()
