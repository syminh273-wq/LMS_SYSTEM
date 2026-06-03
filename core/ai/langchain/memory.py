"""
LangChain hybrid memory.

InMemoryChatMessageHistory  → LLM context window only (pure RAM, volatile).
chat_messages (Cassandra)   → FE display / persistence (read by get_display_messages).

Separation of concerns:
  - The AI reads from RAM. No DB read during conversation.
  - Messages are persisted to Cassandra on every add_message() for FE display.
  - Server restart → RAM is cleared, but Cassandra still has all messages for display.
"""

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# Module-level store — survives between HTTP requests in the same process worker.
_store: dict[str, "HybridChatHistory"] = {}


class HybridChatHistory(InMemoryChatMessageHistory):
    """
    Pure in-memory history for LLM context.
    add_message() also persists to Cassandra (chat_messages) for FE display.
    No DB reads — the LLM always works from RAM.
    """

    def __init__(self, session_id: str):
        super().__init__()
        self._session_id = session_id

    def add_message(self, message: BaseMessage) -> None:
        super().add_message(message)  # → RAM (LLM context)
        # → Cassandra (FE display / persistence)
        from features.ai.repositories.ai_message_repository import AIMessageRepository
        repo = AIMessageRepository()
        if isinstance(message, HumanMessage):
            repo.add_user_message(self._session_id, message.content)
        elif isinstance(message, AIMessage):
            repo.add_ai_message(self._session_id, message.content)


_MAX_HISTORY_MESSAGES = 4  # 2 turns (1 human + 1 AI × 2)

def get_session_history(session_id: str) -> HybridChatHistory:
    """
    Returns the in-memory history for a session, windowed to the last 2 turns.
    Windowing prevents old tool-call answers from poisoning future requests
    when qwen2.5:3b sees prior answers and skips tool calls.
    """
    if session_id not in _store:
        _store[session_id] = HybridChatHistory(session_id)
    hist = _store[session_id]
    if len(hist.messages) > _MAX_HISTORY_MESSAGES:
        hist.messages = hist.messages[-_MAX_HISTORY_MESSAGES:]
    return hist


def invalidate_session(session_id: str) -> None:
    """Evict a session from RAM (call after clear_session)."""
    _store.pop(session_id, None)


def save_turn(session_id: str, question: str, answer: str) -> None:
    """
    Save a user+assistant turn: RAM (LLM context) + Cassandra (FE display).
    Sets session title on first turn and bumps updated_at.
    Used by ConversationMemory (RAGPipeline path).
    """
    from features.ai.repositories.ai_conversation_session_repository import AIConversationSessionRepository
    session_repo = AIConversationSessionRepository()
    mem = get_session_history(session_id)

    if not mem.messages:
        session_repo.set_title(session_id, question[:80])

    mem.add_message(HumanMessage(content=question))
    mem.add_message(AIMessage(content=answer))
    session_repo.touch(session_id)
