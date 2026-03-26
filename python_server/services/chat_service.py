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

SIMILARITY_CSV_THRESHOLD = 0.30

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
        if not message or not model:
            return {"error": "Message and model are required"}, 400
        
        if uploaded_file:
            return self._handle_uploaded_file(
                message=message,
                model=model,
                conversation_history=conversation_history,
                uploaded_file=uploaded_file
            )

        return self._handle_text_only_chat(
            message=message,
            model=model,
            conversation_history=conversation_history
        )

    def _handle_text_only_chat(self, message: str, model: str, conversation_history: list):
        mode = self.router.get_mode(message, conversation_history)
        
        handlers = {
            "grafcet": self._handle_grafcet,
            "agentic": self._handle_agentic,
            "normal": self._handle_normal
        }
        
        handler = handlers.get(mode, self._handle_normal)
        return handler(message, model, conversation_history)

    def _handle_uploaded_file(self, message: str, model: str, 
                            conversation_history: list, uploaded_file: dict):
        file_type = uploaded_file.get("fileType")
        file_id = uploaded_file.get("fileId")

        if not file_id:
            return self._handle_text_only_chat(message, model, conversation_history)

        if file_type in [".csv", "text/csv"]:
            return self._csv_router(message, model, conversation_history, file_id)
        
        elif file_type in [".pdf", "text/pdf"]:
            if not self.vector_store:
                return self._handle_text_only_chat(message, model, conversation_history)
            return self._pdf_router(message, model, conversation_history, file_id)

        return self._handle_text_only_chat(message, model, conversation_history)

    def _handle_agentic(self, message, model, history):
        try:
            executor = self.agent_manager.get_agent(model)
            role_map = {
                "user": HumanMessage,
                "assistant": AIMessage,
            }
            messages = [
                role_map.get(item.get("role"), HumanMessage)(
                    content=item.get("content", "")
                )
                for item in history
            ]

            messages.append(HumanMessage(content=message))
            response = executor.invoke({"input": message})
            clean = clean_response(response.get("output", ""))

            return {
                "response": clean,
                "model": model,
                "timestamp": formatted_datetime(),
                "mode": "agent",
            }

        except Exception as e:
            return {"error": f"Agent error: {str(e)}"}, 501
        
    def _handle_grafcet(self, message, model, history):
        messages = self._build_messages(GRAFCET_SYSTEM_PROMPT, history, message)
        return self._call_ollama(model, messages, temperature=0.0, mode="grafcet")

    def _handle_normal(self, message, model, history):
        messages = self._build_messages(NORMAL_PROMPT, history, message)
        return self._call_ollama(model, messages, temperature=0.0, mode="normal")
        
    def _csv_router(self, message, model, conversation_history, file_id):
        file_path = f'app/uploads/{file_id}.csv'
        csv_keywords = {
            "csv", "data", "column", "row", "filter",
            "table", "sum", "average", "mean", "count",
            "group", "sort", "select"
        }
        if not os.path.exists(file_path):
            return self._handle_text_only_chat(
                message, model, conversation_history
            )
        if any(keyword.lower() in message for keyword in csv_keywords):
            return self._handle_csv(
                message, model, conversation_history, file_path
            )
        if self.router._csv_router(message, model, conversation_history):
            return self._handle_csv(
                message, model, conversation_history, file_path
            )
        
        return self._handle_text_only_chat(
                message, model, conversation_history
            )

    def _handle_csv(self, message: str, model: str, conversation_history: list, file_path: str):
        try:
            df = pd.read_csv(file_path)
            agent_created = self.csv_agent.create_pandas_agent(model, df)
            if not agent_created:
                return self._handle_text_only_chat(message, model, conversation_history)

            print("Using CSV agent")
            results = self.csv_agent.execute_query(message)

            context = str(results) if results else "No relevant data found"
            print(context)

            messages = [
                {"role": item.get("role"), "content": item.get("content")}
                for item in conversation_history
            ]

            messages.append({
                "role": "user",
                "content": CSV_RAG_PROMPT.format(query=message, context=context)
            })
            
            return self._call_ollama(model, messages, temperature=0.0, mode="csv_agent")

        except Exception as e:
            print(f"[CSV ERROR] {e}")
            return self._handle_text_only_chat(message, model, conversation_history)
    
    def _handle_pdf(self, message, model, conversation_history, retrieved_items):
        history_str = format_history(conversation_history, k=3)
        retrieved_items_str = build_context(retrieved_items)
        prompt = RAG_PDF_PROMPT.format(
            query=message,
            history=history_str,
            context=retrieved_items_str
        )
        messages = [{"role": "user", "content": prompt}]
        return self._call_ollama(model, messages, temperature=0.0, mode="rag_pdf")

    def _pdf_router(self, message, model, conversation_history, file_id):
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
                    if max_score > SIMILARITY_CSV_THRESHOLD:
                        print("Using RAG Based of similarity score")
                        return self._handle_pdf(
                            message, model, conversation_history, retrieved_items
                        )
                    elif self.router.check_pdf_rag_eligibility(message, conversation_history, retrieved_items):
                        print("Using RAG after LLM determined its needed")
                        return self._handle_pdf(
                            message, model, conversation_history, retrieved_items
                        )
                    print(max_score)
                    print("Using normal mode because of low similarity score")
                
                print("Using Normal Mode")
                return self._handle_text_only_chat(
                    message, model, conversation_history
                )

        except Exception as e:
            print(f"RAG retrieval error: {str(e)}")
            return self._handle_text_only_chat(
                message, model, conversation_history
            )
        
    def _call_ollama(self, model: str, messages: list, temperature: float = 0.0, mode: str = "normal"):
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature}
            }

            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=600
            )
            resp.raise_for_status()
            
            content = resp.json()["message"]["content"]
            cleaned = clean_response(content)

            return {
                "response": cleaned,
                "model": model,
                "timestamp": formatted_datetime(),
                "mode": mode
            }

        except requests.exceptions.Timeout:
            return {"error": "Request to Ollama timed out"}, 504
        except requests.exceptions.HTTPError as e:
            return {"error": f"Ollama HTTP error: {str(e)}"}, 502
        except Exception as e:
            print(f"Ollama call error: {str(e)}")
            return {"error": f"Failed to get response from model: {str(e)}"}, 500
        
    def _build_messages(self, system_prompt: str, history: list, user_message: str) -> list:
        """
        Builds consistent message format for Ollama.
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        for item in history:
            messages.append({
                "role": item.get("role", "user"),
                "content": item.get("content", "")
            })
        
        messages.append({"role": "user", "content": user_message})
        return messages