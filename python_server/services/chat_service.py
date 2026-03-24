from flask import jsonify
import requests
from config import OLLAMA_BASE_URL
from utils.response_cleaner import clean_response, boolean_filter
from utils.basic_utils import formatted_datetime
from core.agent_manager import AgenticMode, CSVAgent
from core.router import Router
from prompts.grafcet_prompt import GRAFCET_SYSTEM_PROMPT
from prompts.normal_prompt import NORMAL_PROMPT
from prompts.csv_rag_prompt import CSV_RAG_PROMPT
from prompts.csv_agent_eligibility import CSV_AGENT_ELIGIBILITY
from langchain_core.messages import HumanMessage, AIMessage
import os
import pandas as pd

class ChatService:

    agent_manager = AgenticMode()
    router = Router()
    csv_agent = CSVAgent()
    vector_store = None  # Will be initialized in app.py

    @staticmethod
    def handle_chat(data: dict):
        message = data.get("message")
        model = data.get("model")
        conversation_history = data.get("conversationHistory", [])
        uploaded_file = data.get("uploadedFile", None)
        print(uploaded_file)
        if not message or not model:
            return {"error": "Message and model are required"}, 400
        
        if uploaded_file and ChatService.vector_store:
            return ChatService._generate_rag_response(message, model, conversation_history, uploaded_file)

        return ChatService._generate_response(message, model, conversation_history)
    
    @staticmethod
    def _generate_rag_response(message, model, conversation_history, uploaded_file):
        file_type = os.path.splitext(uploaded_file.get("fileName"))[1]
        file_id = uploaded_file.get("fileId", None)

        if not file_id:
            return ChatService._generate_response(message, model, conversation_history)
        if file_type == ".csv":
            return ChatService._handle_csv_agent(message=message, model=model, conversation_history=conversation_history, file_id=file_id)
        elif file_type == ".pdf":
            return ChatService._handle_pdf_rag(message=message, model=model, conversation_history=conversation_history, file_id=file_id)
        
        return ChatService._generate_response(message, model, conversation_history)

    @staticmethod
    def _generate_response(message, model, conversation_history):
        mode = ChatService.router.get_mode(message, conversation_history)
        if mode == "grafcet":
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
                "timestamp": formatted_datetime(),
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
    def _handle_normal_mode(message, model, history):
        try:
            messages = [{"role": "system", "content": NORMAL_PROMPT}]

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
        
    @staticmethod
    def _handle_csv_agent(message, model, conversation_history, file_id):
        file_path = f'uploads/{file_id}.csv'
        csv_keywords = {
            "csv", "data", "column", "row", "filter",
            "table", "sum", "average", "mean", "count",
            "group", "sort", "select"
        }
        if not os.path.exists(file_path):
            return ChatService._generate_response(
                message, model, conversation_history
            )
        if any(keyword in message for keyword in csv_keywords):
            return ChatService._generate_csv_response(
                message, model, conversation_history, file_path
            )
        if ChatService._csv_router(message, model, conversation_history):
            return ChatService._generate_csv_response(
                message, model, conversation_history, file_path
            )
        
        return ChatService._generate_response(
                message, model, conversation_history
            )

    @staticmethod
    def _csv_router(message, model, conversation_history):
        history_summary = "\n".join( f"{m.get('role', 'user')}: {m.get('content', '')[:140]}..." for m in conversation_history[-3:] ) or "No history."

        payload = {
            "model": model, # or tiny fast model
            "messages": [
                {"role": "user", "content": CSV_AGENT_ELIGIBILITY.format(
                    query=message,
                    history=history_summary
                )}
            ],
            "stream": False,
            "options": {"temperature": 0.0}
        }

        try:
            r = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=15)
            r.raise_for_status() # Break if HTTP failed
            text = r.json()["message"]["content"].strip()
            use_csv_agent = boolean_filter(text)
            if (use_csv_agent is not None):
                return use_csv_agent
            else:
                return False

        except Exception as e:
            print(f"Router error: {e}") # For now
            return False

    @staticmethod
    def _generate_csv_response(message, model, conversation_history, file_path):
        df = pd.read_csv(file_path)
        results = None
        if ChatService.csv_agent.create_pandas_agent(model, df):
            results = ChatService.csv_agent.execute_query(message)
            print("Using csv agent")
            context=str(results) if results else "No relevant data found"
            print(context)
            messages = []

            for item in conversation_history:
                messages.append({
                    "role": item.get("role"),
                    "content": item.get("content")
                })

            messages.append({
                "role": "user",
                "content": CSV_RAG_PROMPT.format(
                    query=message,
                    context=context
                )
            })

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
                "mode": "csv_rag"
            }
        return ChatService._generate_response(
                message, model, conversation_history
            ) 

    @staticmethod
    def _handle_pdf_rag(message, file_id):
        try:
            if file_id:
                retrieved_items = ChatService.vector_store.retrieve(
                    query=message,
                    collection_name=file_id,
                    k=5 
                )
                print(f"Retrieved {len(retrieved_items)} items from vector DB")
                return retrieved_items
        except Exception as e:
            print(f"RAG retrieval error: {str(e)}")
            retrieved_items = []