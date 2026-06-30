"""ConversationState 扩展字段测试"""

from app.services.conversation.state import ConversationState, PendingAction


class TestConversationState:
    def test_pending_action_field_optional(self) -> None:
        state: ConversationState = {"user_message": "test", "current_user_id": "u1"}
        assert state.get("pending_action") is None

    def test_pending_action_field_set(self) -> None:
        action: PendingAction = {
            "intent": "status_change",
            "params": {"candidate_name": "张三", "target_status": "interview"},
        }
        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": "u1",
            "pending_action": action,
        }
        assert state["pending_action"]["intent"] == "status_change"

    def test_pending_action_clear(self) -> None:
        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": "u1",
            "pending_action": {"intent": "job_status", "params": {"job_code": "J04217", "action": "close"}},
        }
        # Clearing is represented by returning None from a node
        cleared: ConversationState = {**state, "pending_action": None}
        assert cleared["pending_action"] is None
