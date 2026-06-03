"""
OllamaLangChainLLM — wraps AIClient into a proper LangChain BaseChatModel.

Implements bind_tools() so create_tool_calling_agent can use it.
Converts between LangChain message objects and Ollama dict format.
"""

import json
import uuid
from typing import Any, Iterator, List, Optional, Sequence, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.utils.function_calling import convert_to_openai_tool

from core.ai.llm.services.ai_client import AIClient


def _to_dict(message: BaseMessage) -> dict:
    """Convert a LangChain message object to an Ollama-compatible dict."""
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": str(message.content)}
    if isinstance(message, AIMessage):
        msg: dict = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            msg["tool_calls"] = [
                {
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["args"],
                    }
                }
                for tc in message.tool_calls
            ]
        return msg
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": str(message.content)}
    if isinstance(message, ToolMessage):
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "content": str(message.content),
        }
    return {"role": "user", "content": str(message.content)}


def _parse_tool_calls(raw_calls: list) -> list:
    """Convert Ollama tool_calls to LangChain tool_calls format."""
    result = []
    for tc in raw_calls or []:
        fn = tc.get("function", {})
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        result.append({
            "name": fn.get("name", ""),
            "args": args,
            "id": tc.get("id", str(uuid.uuid4())),
            "type": "tool_call",
        })
    return result


class OllamaLangChainLLM(BaseChatModel):
    """
    LangChain BaseChatModel wrapping AIClient (Ollama).
    Supports bind_tools() for create_tool_calling_agent.
    """

    model: str = "qwen2.5:3b"
    timeout: int = 120
    temperature: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "ollama"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs: Any,
    ) -> ChatResult:
        msg_dicts = [_to_dict(m) for m in messages]
        tools: list = kwargs.get("tools") or []

        if tools:
            raw = AIClient.chat_with_tools(msg_dicts, tools=tools, timeout=self.timeout)
            content = raw.get("content") or ""
            lc_tool_calls = _parse_tool_calls(raw.get("tool_calls") or [])
            ai_msg = AIMessage(content=content, tool_calls=lc_tool_calls)
        else:
            content = AIClient.chat_sync(msg_dicts, timeout=self.timeout)
            ai_msg = AIMessage(content=content)

        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """
        Stream response from AIClient.chat_stream.
        """
        msg_dicts = [_to_dict(m) for m in messages]
        tools: list = kwargs.get("tools") or []

        for chunk in AIClient.chat_stream(msg_dicts, tools=tools, timeout=self.timeout):
            if isinstance(chunk, str):
                if run_manager:
                    run_manager.on_llm_new_token(chunk)
                yield ChatGenerationChunk(message=AIMessageChunk(content=chunk))
            elif isinstance(chunk, tuple):
                signal, data = chunk
                if signal == "__TOOL_CALLS__":
                    lc_tool_calls = _parse_tool_calls(data)
                    yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_calls=lc_tool_calls))
                elif signal == "__FULL__":
                    # End of stream
                    pass
                elif signal == "__ERROR__":
                    raise RuntimeError(f"Ollama stream error: {data}")

    def bind_tools(
        self,
        tools: Sequence[Union[dict, type, Any]],
        *,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Runnable:
        """Convert LangChain tools to OpenAI/Ollama schema and bind to this LLM."""
        converted = [convert_to_openai_tool(t) for t in tools]
        return self.bind(tools=converted, **kwargs)
