from typing import List

from langchain.memory import ConversationBufferWindowMemory

from features.ai.services.langchain_chat_history import CassandraMessageHistory


class ShortTermMemoryManager:
    """
    Wraps CassandraMessageHistory with a k-turn window for LLM context.
    All messages are persisted in chat_messages; only the last k turns are
    sent to the LLM to keep token usage bounded.
    """

    def __init__(self, session_id: str, k: int = 5):
        self.session_id = session_id
        self.history = CassandraMessageHistory(session_id)
        self.memory = ConversationBufferWindowMemory(
            chat_memory=self.history,
            k=k,
            return_messages=True,
        )

    def get_context(self) -> List[dict]:
        """Returns last k turns as [{'role': ..., 'content': ...}] for LLM."""
        lc_msgs = self.memory.load_memory_variables({}).get('history', [])
        result = []
        for m in lc_msgs:
            from langchain_core.messages import HumanMessage, AIMessage
            role = 'user' if isinstance(m, HumanMessage) else 'assistant'
            result.append({'role': role, 'content': m.content})
        return result

    def save_turn(self, question: str, answer: str) -> None:
        """Persists one user+assistant turn to chat_messages."""
        self.memory.save_context(
            {'input': question},
            {'output': answer},
        )
