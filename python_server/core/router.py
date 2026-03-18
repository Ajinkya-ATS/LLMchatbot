import requests
from utils.response_cleaner import mode_selection, boolean_filter
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config import OLLAMA_BASE_URL
from prompts.mode_selection_prompt import MODE_SELECTION_PROMPT
from prompts.rag_eligibility_checker_prompt import RAG_ELIGIBILITY_PROMPT


ROUTER_MODEL = "gpt-oss:120b-cloud"

class Router: # Mode means, agentic, grafcet or simple
    
    @staticmethod
    def get_mode(message: str, history: list, retrieved_items: list = None) -> str:

        #Just taking last 3 messages in history
        history_summary = "\n".join( f"{m.get('role', 'user')}: {m.get('content', '')[:140]}..." for m in history[-3:] ) or "No history."
        
        # Format retrieved context for the prompt
        if retrieved_items and len(retrieved_items) > 0:
            retrieved_context = "\n---\n".join(retrieved_items[:3])  # Use top 3 retrieved items
        else:
            retrieved_context = "No documents retrieved."

        # directly hit ollama
        payload = {
            "model": ROUTER_MODEL, # or tiny fast model
            "messages": [
                {"role": "user", "content": MODE_SELECTION_PROMPT.format(
                    history_summary=history_summary,
                    message=message,
                    retrieved_context=retrieved_context
                )}
            ],
            "stream": False,
            "options": {"temperature": 0.0}
        }

        try:
            r = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=15)
            r.raise_for_status() # Break if HTTP failed
            text = r.json()["message"]["content"].strip()
            match = mode_selection(text)
            if (match is not None):
                return match
            else:
                return "normal"

        except Exception as e:
            print(f"Router error: {e}") # For now
            return "normal"
        
    @staticmethod
    def check_rag_eligibility(message: str, history: list, retrieved_items) -> bool:

        #Just taking last 3 messages in history
        history_summary = "\n".join( f"{m.get('role', 'user')}: {m.get('content', '')[:140]}..." for m in history[-3:] ) or "No history."

        payload = {
            "model": ROUTER_MODEL, # or tiny fast model
            "messages": [
                {"role": "user", "content": RAG_ELIGIBILITY_PROMPT.format(
                    retrieved_items=retrieved_items,
                    history_summary=history_summary,
                    message=message
                )}
            ],
            "stream": False,
            "options": {"temperature": 0.0}
        }

        try:
            r = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=15)
            r.raise_for_status() # Break if HTTP failed
            text = r.json()["message"]["content"].strip()
            return boolean_filter(text)
        
        except Exception as e:
            print(f"Router error: {e}") # For now
            return False