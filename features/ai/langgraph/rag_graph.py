from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from core.ai.rag.services.rag_pipeline import RAGPipeline
from core.ai.llm.services.ai_client import AIClient
from features.ai.langgraph.cassandra_saver import CassandraSaver

class State(TypedDict):
    messages: Annotated[list, add_messages]
    context: str
    classroom_id: str

class LangGraphRAGService:
    """
    Standardized AI Workflow using LangGraph.
    Decouples AI logic from specific database models.
    """
    
    def __init__(self):
        self.pipeline = RAGPipeline()
        self.saver = CassandraSaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(State)
        
        # 1. Retrieve Context
        def retrieve(state: State):
            last_message = state['messages'][-1].content
            hits = self.pipeline.search(last_message, filter_meta={'classroom_id': state['classroom_id']})
            context = "\n\n---\n\n".join(h["document"] for h in hits) if hits else ""
            return {"context": context}

        # 2. Generate Answer
        def generate(state: State):
            system_prompt = (
                "Bạn là một trợ lý ảo hữu ích. Hãy trả lời câu hỏi của người dùng CHỈ bằng cách sử dụng ngữ cảnh được cung cấp.\n\n"
                f"Ngữ cảnh:\n{state['context']}"
            )
            # Combine state messages for LLM
            llm_messages = [{"role": "system", "content": system_prompt}]
            for m in state['messages']:
                role = "user" if isinstance(m, HumanMessage) else "assistant"
                llm_messages.append({"role": role, "content": m.content})
            
            answer = AIClient.chat_sync(llm_messages)
            return {"messages": [AIMessage(content=answer)]}

        workflow.add_node("retrieve", retrieve)
        workflow.add_node("generate", generate)
        
        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile(checkpointer=self.saver)

    def ask(self, question: str, classroom_id: str, session_id: str):
        config = {"configurable": {"thread_id": session_id}}
        input_state = {
            "messages": [HumanMessage(content=question)],
            "classroom_id": classroom_id
        }
        final_state = self.graph.invoke(input_state, config=config)
        return {
            "answer": final_state["messages"][-1].content,
            "session_id": session_id
        }
