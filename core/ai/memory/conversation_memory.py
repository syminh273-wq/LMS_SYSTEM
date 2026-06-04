from typing import List


class ConversationMemory:
    """
    Thin facade used by RAGPipeline.
    Delegates to AIMessageRepository so history comes from chat_messages.
    """

    _repo = None

    @classmethod
    def _get_repo(cls):
        if cls._repo is None:
            from features.ai.repositories.ai_message_repository import AIMessageRepository
            cls._repo = AIMessageRepository()
        return cls._repo

    def get_history(self, session_id: str) -> List[dict]:
        return self._get_repo().get_history_for_llm(session_id, max_turns=5)

    def save_turn(self, session_id: str, question: str, answer: str) -> None:
        from features.ai.services.ai_conversation_session_service import AIConversationSessionService
        AIConversationSessionService().save_turn(session_id, question, answer)

    def get_langgraph_checkpointer(self):
        from features.ai.langgraph.cassandra_saver import CassandraSaver
        return CassandraSaver()
