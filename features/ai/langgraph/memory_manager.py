from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage
from core.ai.memory.conversation_memory import ConversationMemory

_memory = ConversationMemory()

class MemoryState(TypedDict):
    # LangGraph will automatically handle appending to this list
    messages: Annotated[list, add_messages]

class LangGraphMemoryManager:
    """
    Focused tool to use LangGraph for standardized memory management
    while keeping your existing RAG/AI logic outside.
    """
    
    def __init__(self):
        self.checkpointer = _memory.get_langgraph_checkpointer()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(MemoryState)
        
        # Simple "pass-through" node that just ensures state is saved
        def sync_memory(state: MemoryState):
            return state

        workflow.add_node("sync", sync_memory)
        workflow.add_edge(START, "sync")
        workflow.add_edge("sync", END)
        
        return workflow.compile(checkpointer=self.checkpointer)

    def load_history(self, session_id: str) -> list:
        """Load history using LangGraph's state management."""
        config = {"configurable": {"thread_id": session_id}}
        state = self.graph.get_state(config)
        return state.values.get("messages", []) if state.values else []

    def save_chat_turn(self, session_id: str, question: str, answer: str):
        """Save a new turn into the standardized LangGraph state."""
        config = {"configurable": {"thread_id": session_id}}
        self.graph.update_state(config, {
            "messages": [
                HumanMessage(content=question),
                AIMessage(content=answer)
            ]
        })
