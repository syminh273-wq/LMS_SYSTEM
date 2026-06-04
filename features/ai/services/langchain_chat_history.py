from typing import List

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from features.ai.repositories.ai_message_repository import AIMessageRepository
from features.ai.repositories.ai_conversation_session_repository import AIConversationSessionRepository


class CassandraMessageHistory(BaseChatMessageHistory):
    """
    LangChain chat history backed by chat_messages table.
    session_id is used as conversation_uid.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._msg_repo = AIMessageRepository()
        self._session_repo = AIConversationSessionRepository()

    @property
    def messages(self) -> List[BaseMessage]:
        lc_msgs = []
        for m in self._msg_repo.get_display_messages(self.session_id):
            if m['role'] == 'user':
                lc_msgs.append(HumanMessage(content=m['content']))
            else:
                lc_msgs.append(AIMessage(content=m['content']))
        return lc_msgs

    def add_message(self, message: BaseMessage) -> None:
        is_first = self._msg_repo.is_first_message(self.session_id)

        if isinstance(message, HumanMessage):
            if is_first:
                self._session_repo.set_title(self.session_id, message.content[:80])
            self._msg_repo.add_user_message(self.session_id, message.content)
        else:
            self._msg_repo.add_ai_message(self.session_id, message.content)

        self._session_repo.touch(self.session_id)

    def clear(self) -> None:
        pass  # Soft delete handled at the session level; no bulk clear needed
