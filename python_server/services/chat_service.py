from flask import jsonify
from datetime import datetime
import requests
from config import OLLAMA_BASE_URL
from utils.response_cleaner import clean_response
from core.agent_manager import AgentManager
from core.router import ModeRouter
from prompts.grafcet_prompt import GRAFCET_SYSTEM_PROMPT
from langchain_core.messages import HumanMessage, AIMessage

class ChatService:

    agent_manager = AgentManager()
    router = ModeRouter()

    @staticmethod
    def handle_chat(data: dict):
        message = data.get("message")
        model = data.get("model")
        conversation_history = data.get("conversationHistory", [])

        if not message or not model:
            return {"error": "Message and model are required"}, 400
        
        mode = ChatService.router.get_mode(message, conversation_history)

        if mode == "grafcet": # Maybe we should replace it with 0,1,2 in future instead of raw strings
            return ChatService._handle_grafcet_mode(message, model, conversation_history)
        elif mode == "agentic":
            return ChatService._handle_agent_mode(message, model, conversation_history)
        else:
            return ChatService._handle_normal_mode(message, model, conversation_history)

    @staticmethod
    def _handle_agent_mode(message, model, history):
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
                "mode": "agent"
            }
        except Exception as e:
            return {"error": f"Agent error: {str(e)}"}, 501
        
    @staticmethod
    def _handle_grafcet_mode(message, model, history):
        try:
            messages = [{"role": "system", "content": GRAFCET_SYSTEM_PROMPT}]
            for item in history:
                messages.append({"role": item.get("role"), "content": item.get("content")})
            messages.append({"role": "user", "content": message})

            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
                timeout=60
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]

            return {
                "response": clean_response(content),
                "model": model,
                "mode": "normal"
            }
        except Exception as e:
            return {"error": f"Normal chat error: {str(e)}"}, 502

    @staticmethod
    def _handle_normal_mode(message, model, history):
        try:
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            for item in history:
                messages.append({"role": item.get("role"), "content": item.get("content")})
            messages.append({"role": "user", "content": message})

            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
                timeout=60
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]

            return {
                "response": clean_response(content),
                "model": model,
                "mode": "normal"
            }
        except Exception as e:
            return {"error": f"Normal chat error: {str(e)}"}, 503