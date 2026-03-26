from flask import jsonify
import requests
from config import OLLAMA_BASE_URL
from utils.response_cleaner import clean_response, boolean_filter
from utils.basic_utils import formatted_datetime, format_history, build_context
from core.agent_manager import AgenticMode, CSVAgent
from core.router import Router
from prompts.grafcet_prompt import GRAFCET_SYSTEM_PROMPT
from prompts.normal_prompt import NORMAL_PROMPT
from prompts.csv_rag_prompt import CSV_RAG_PROMPT
from prompts.rag_pdf_prompt import RAG_PDF_PROMPT
from langchain_core.messages import HumanMessage, AIMessage
import os
import pandas as pd

class ChatService:

    def __init__(self, vector_store=None):
        self.agent_manager = AgenticMode()
        self.router = Router()
        self.csv_agent = CSVAgent()
        self.vector_store = vector_store

    def handle_chat(self, data: dict):
        message = data.get("message")
        model = data.get("model")
        conversation_history = data.get("conversationHistory", [])
        uploaded_file = data.get("uploadedFile", None)
        print(uploaded_file)
        if not message or not model:
            return {"error": "Message and model are required"}, 400
        
        if uploaded_file:
            return self._generate_rag_response(message, model, conversation_history, uploaded_file)

        return self._generate_response(message, model, conversation_history)
    
    def _generate_rag_response(self, message, model, conversation_history, uploaded_file):
        file_type = uploaded_file.get("fileType", None)
        file_id = uploaded_file.get("fileId", None)

        if not file_id:
            return self._generate_response(message, model, conversation_history)
        if file_type == ".csv" or file_type == "text/csv":
            return self._handle_csv_agent(message=message, model=model, conversation_history=conversation_history, file_id=file_id)
        elif file_type == ".pdf" or file_type == "text/pdf":
            if not self.vector_store:
                return self._generate_response(message, model, conversation_history)
            return self._handle_pdf_rag(message=message, model=model, conversation_history=conversation_history, file_id=file_id)
        
        return self._generate_response(message, model, conversation_history)

    def _generate_response(self, message, model, conversation_history):
        mode = self.router.get_mode(message, conversation_history)
        if mode == "grafcet":
            return self._handle_grafcet_mode(message, model, conversation_history)
        elif mode == "agentic":
            return self._handle_agent_mode(message, model, conversation_history)
        else:
            return self._handle_normal_mode(message, model, conversation_history)

    def _handle_agent_mode(self, message, model, history):
        try:
            executor = self.agent_manager.get_agent(model)
            
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
        
    def _handle_grafcet_mode(self, message, model, history):
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

    def _handle_normal_mode(self, message, model, history):
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
        
    def _handle_csv_agent(self, message, model, conversation_history, file_id):
        file_path = f'app/uploads/{file_id}.csv'
        csv_keywords = {
            "csv", "data", "column", "row", "filter",
            "table", "sum", "average", "mean", "count",
            "group", "sort", "select"
        }
        if not os.path.exists(file_path):
            return self._generate_response(
                message, model, conversation_history
            )
        if any(keyword in message for keyword in csv_keywords):
            return self._generate_csv_response(
                message, model, conversation_history, file_path
            )
        if self.router._csv_router(message, model, conversation_history):
            return self._generate_csv_response(
                message, model, conversation_history, file_path
            )
        
        return self._generate_response(
                message, model, conversation_history
            )

    def _generate_csv_response(self, message, model, conversation_history, file_path):
        try:
            df = pd.read_csv(file_path)
            results = None
            if self.csv_agent.create_pandas_agent(model, df):
                results = self.csv_agent.execute_query(message)
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
            return self._generate_response(
                    message, model, conversation_history
                )
        except Exception as e:
            print(f"CSV error: {str(e)}")
            return self._generate_response(
                message, model, conversation_history
            )
    
    def _generate_pdf_response(self, message, model, conversation_history, retrieved_items):
        history_str = format_history(conversation_history, k=3)
        retrieved_items_str = build_context(retrieved_items)
        print(retrieved_items_str)
        payload = {
            "model": model, # or tiny fast model
            "messages": [
                {"role": "user", "content": RAG_PDF_PROMPT.format(
                    query=message,
                    history=history_str,
                    context = retrieved_items_str
                )}
            ],
            "stream": False,
            "options": {"temperature": 0.0}
        }

        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=600
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]

        return {
            "response": clean_response(content),
            "model": model,
            "timestamp": formatted_datetime(),
            "mode": "rag_pdf"
        }

    def _handle_pdf_rag(self, message, model, conversation_history, file_id):
        try:
            if file_id:
                retrieved_items = self.vector_store.retrieve(
                    query=message,
                    query_history = conversation_history,
                    collection_name=file_id,
                    k=5
                )
                max_score = 0
                if retrieved_items:
                    max_score = max(item["score"] for item in retrieved_items if item["score"] is not None)
                    if max_score > 0.30:
                        print("Using RAG Based of similarity score")
                        return self._generate_pdf_response(
                            message, model, conversation_history, retrieved_items
                        )
                    elif self.router.check_pdf_rag_eligibility(message, conversation_history, retrieved_items):
                        print("Using RAG after LLM determined its needed")
                        return self._generate_pdf_response(
                            message, model, conversation_history, retrieved_items
                        )
                    print(max_score)
                    print("Using normal mode because of low similarity score")
                
                print("Using Normal Mode")
                return self._generate_response(
                    message, model, conversation_history
                )

        except Exception as e:
            print(f"RAG retrieval error: {str(e)}")
            return self._generate_response(
                message, model, conversation_history
            )