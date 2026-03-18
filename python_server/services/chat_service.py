from flask import jsonify
import requests
from config import OLLAMA_BASE_URL
from utils.response_cleaner import clean_response
from utils.basic_utils import formatted_datetime
from core.agent_manager import AgentManager
from core.router import Router
from prompts.grafcet_prompt import GRAFCET_SYSTEM_PROMPT
from prompts.normal_prompt import NORMAL_PROMPT
from langchain_core.messages import HumanMessage, AIMessage

class ChatService:

    agent_manager = AgentManager()
    router = Router()
    vector_store = None  # Will be initialized in app.py

    @staticmethod
    def handle_chat(data: dict):
        message = data.get("message")
        model = data.get("model")
        conversation_history = data.get("conversationHistory", [])
        uploaded_file = data.get("uploadedFile", None)

        if not message or not model:
            return {"error": "Message and model are required"}, 400
        
        retrieved_items = []
        
        # First, retrieve documents if a file was uploaded
        if uploaded_file and ChatService.vector_store:
            try:
                file_id = uploaded_file.get("fileId")
                if file_id:
                    retrieved_items = ChatService.vector_store.retrieve(
                        query=message,
                        collection_name=file_id,
                        k=5
                    )
                    print(f"Retrieved {len(retrieved_items)} items from vector DB")
            except Exception as e:
                print(f"RAG retrieval error: {str(e)}")
                retrieved_items = []
        
        # Now get mode with RAG context awareness
        mode = ChatService.router.get_mode(message, conversation_history, retrieved_items)
        
        # Check RAG eligibility after mode selection
        if retrieved_items:
            use_rag = ChatService.router.check_rag_eligibility(message, conversation_history, retrieved_items)
            if not use_rag:
                retrieved_items = []
                print("RAG documents not relevant for this query")
        
        print(mode) # Temporary print
        if mode == "grafcet": # Maybe we should replace it with 0,1,2 in future instead of raw strings
            return ChatService._handle_grafcet_mode(message, model, conversation_history, retrieved_items)
        elif mode == "agentic":
            return ChatService._handle_agent_mode(message, model, conversation_history, retrieved_items)
        else:
            return ChatService._handle_normal_mode(message, model, conversation_history, retrieved_items)

    @staticmethod
    def _handle_agent_mode(message, model, history, retrieved_items=None):
        try:
            executor = ChatService.agent_manager.get_agent(model)
            
            # Convert conversation history to LangChain messages
            messages = []
            for item in history:
                role = item.get("role", "user")
                content = item.get("content", "")
                
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
            
            # Add retrieved context if available
            if retrieved_items:
                context = "\n\n".join(retrieved_items)
                context_message = f"Retrieved context from uploaded documents:\n{context}"
                messages.append(AIMessage(content=context_message))
            
            # Add the current message
            messages.append(HumanMessage(content=message))
            
            # Invoke the executor with input parameter
            response = executor.invoke({"input": message})

            # Extract the response
            final_message = response["output"]
            clean = clean_response(final_message)

            return {
                "response": clean,
                "model": model,
                "timestamp": formatted_datetime(),
                "mode": "agent"
            }
        except Exception as e:
            return {"error": f"Agent error: {str(e)}"}, 501
        
    @staticmethod
    def _handle_grafcet_mode(message, model, history, retrieved_items=None):
        try:
            messages = [{"role": "system", "content": GRAFCET_SYSTEM_PROMPT}]
            
            # Add retrieved context if available
            if retrieved_items:
                context = "\n\n".join(retrieved_items)
                messages.append({"role": "system", "content": f"Retrieved context from documents:\n{context}"})
            
            for item in history:
                messages.append({"role": item.get("role"), "content": item.get("content")})
            messages.append({"role": "user", "content": message})

            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
                timeout=600
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]

            return {
                "response": clean_response(content),
                "model": model,
                "timestamp": formatted_datetime(),
                "mode": "grafcet"
            }
        except Exception as e:
            return {"error": f"Normal chat error: {str(e)}"}, 502

    @staticmethod
    def _handle_normal_mode(message, model, history, retrieved_items=None):
        try:
            messages = [{"role": "system", "content": NORMAL_PROMPT}]
            
            # Add retrieved context if available
            if retrieved_items:
                context = "\n\n".join(retrieved_items)
                messages.append({"role": "system", "content": f"Retrieved context from documents:\n{context}"})
            
            for item in history:
                messages.append({"role": item.get("role"), "content": item.get("content")})
            messages.append({"role": "user", "content": message})

            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
                timeout=600
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]

            return {
                "response": clean_response(content),
                "model": model,
                "timestamp": formatted_datetime(),
                "mode": "normal"
            }
        except Exception as e:
            return {"error": f"Normal chat error: {str(e)}"}, 503