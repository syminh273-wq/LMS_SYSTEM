"""
LMSAgent — LangChain-native agent with tools + in-memory conversation history.

Uses:
  - ChatOllama            : LLM with tool-calling support
  - create_tool_calling_agent : ReAct-style agent built by LangChain
  - AgentExecutor         : manages the tool-call loop
  - RunnableWithMessageHistory : wires HybridChatHistory (RAM + Cassandra)
"""

import queue
import threading
from typing import Any, Generator, Union

from decouple import config
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from core.ai.langchain.llm import OllamaLangChainLLM
from core.ai.langchain.memory import get_session_history

_TOOL_MODEL = config("OLLAMA_TOOL_MODEL", default="qwen2.5:3b")

_DEFAULT_SYSTEM = (
    "Bạn là trợ lý AI thông minh của hệ thống LMS. "
    "Sử dụng các công cụ được cung cấp để lấy thông tin chính xác. "
    "Khi người dùng yêu cầu tóm tắt, phân tích chi tiết hoặc 'đọc sâu' tài liệu, "
    "hãy sử dụng công cụ search_documents với top_k từ 10 đến 15 để có đủ ngữ cảnh. "
    "Trả lời bằng tiếng Việt, văn phong chuyên nghiệp và chính xác."
)


class TokenHandler(BaseCallbackHandler):
    """Callback to capture tokens for streaming."""
    def __init__(self, q: queue.Queue):
        self.q = q

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.q.put(token)


class LMSAgent:
    """
    LangChain agent with:
    - Tool calling (search_documents + classroom tools)
    - Automatic conversation memory via RunnableWithMessageHistory
    - In-memory history (RAM), persisted to Cassandra on each turn
    """

    def __init__(self, tools: list, system_prompt: str = None):
        llm = OllamaLangChainLLM(model=_TOOL_MODEL)

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt or _DEFAULT_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        self._executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
        )

        self._chain = RunnableWithMessageHistory(
            self._executor,
            get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    def ask(self, question: str, session_id: str) -> dict:
        """Synchronous invoke. Returns answer + tool_calls used."""
        result = self._chain.invoke(
            {"input": question},
            config={"configurable": {"session_id": session_id}},
        )
        tool_calls = [
            {"tool": step[0].tool, "args": step[0].tool_input, "result": step[1]}
            for step in result.get("intermediate_steps", [])
        ]
        return {
            "answer":     result.get("output", ""),
            "tool_calls": tool_calls,
            "session_id": session_id,
        }

    def ask_stream(self, question: str, session_id: str) -> Generator[Union[str, tuple], None, None]:
        """
        Yields answer text in chunks and tool calls if any.
        Uses a separate thread and a queue to capture tokens via callback.
        """
        q = queue.Queue()
        handler = TokenHandler(q)

        def _run():
            try:
                for chunk in self._chain.stream(
                    {"input": question},
                    config={
                        "configurable": {"session_id": session_id},
                        "callbacks": [handler]
                    },
                ):
                    if "actions" in chunk:
                        tool_calls = [
                            {"tool": a.tool, "args": a.tool_input}
                            for a in chunk["actions"]
                        ]
                        q.put(("__TOOL_CALLS__", tool_calls))
            except Exception as e:
                q.put(("__ERROR__", str(e)))
            finally:
                q.put(None)

        threading.Thread(target=_run, daemon=True).start()

        while True:
            item = q.get()
            if item is None:
                break
            yield item
