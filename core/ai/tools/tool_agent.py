"""
ToolAgent — ReAct-style agent loop.

Flow:
  1. Send messages + tools to LLM
  2. If response contains tool_calls → execute each → append results → repeat
  3. If response is plain text (no tool_calls) → return as final answer
  4. Stop after MAX_ITERATIONS to prevent infinite loops
"""

import json
from typing import List, Optional

from core.ai.llm.services.ai_client import AIClient
from core.ai.memory.conversation_memory import ConversationMemory

_memory = ConversationMemory()

MAX_ITERATIONS = 5

_SYSTEM_PROMPT = (
    "Bạn là trợ lý AI thông minh của hệ thống LMS (Learning Management System). "
    "Bạn có thể sử dụng các công cụ (tools) được cung cấp để lấy thông tin chính xác từ hệ thống. "
    "Hãy sử dụng tool khi cần thiết, sau đó tổng hợp kết quả và trả lời người dùng. "
    "Trả lời bằng tiếng Việt, ngắn gọn và chính xác."
)


class ToolAgent:

    def run(
        self,
        question: str,
        tools: List[dict],
        executor,
        system_prompt: str = None,
        context: dict = None,
        timeout: int = 120,
        session_id: Optional[str] = None,
    ) -> dict:
        base_prompt = system_prompt or _SYSTEM_PROMPT
        if context:
            ctx_lines = "\n".join(f"- {k}: {v}" for k, v in context.items())
            base_prompt += f"\n\nThông tin ngữ cảnh hiện tại:\n{ctx_lines}\nHãy dùng các thông tin này khi gọi tool."

        history = _memory.get_history(session_id) if session_id else []
        messages = [{"role": "system", "content": base_prompt}] + history + [{"role": "user", "content": question}]
        tool_call_log = []

        for iteration in range(MAX_ITERATIONS):
            print(f"[ToolAgent] iteration {iteration + 1}/{MAX_ITERATIONS}")
            response = AIClient.chat_with_tools(messages, tools=tools, timeout=timeout)

            tool_calls = response.get("tool_calls")

            # No tool calls → final answer
            if not tool_calls:
                answer = response.get("content", "")
                if session_id and answer:
                    _memory.save_turn(session_id, question, answer)

                return {
                    "answer": answer,
                    "tool_calls": tool_call_log,
                    "session_id": session_id,
                }

            # Append assistant turn (with tool_calls) to history
            messages.append({
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": tool_calls,
            })

            # Execute each tool call and append tool result messages
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except Exception:
                    args = {}

                print(f"[ToolAgent] calling {name}({args})")
                result = executor.execute(name, args)

                tool_call_log.append({
                    "tool": name,
                    "args": args,
                    "result": result,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result,
                })

        return {
            "answer": "Đã vượt quá giới hạn vòng lặp tool calling.",
            "tool_calls": tool_call_log,
        }
