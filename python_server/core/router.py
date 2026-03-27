import requests
from utils.response_cleaner import mode_selection, boolean_filter
from utils.basic_utils import build_context
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config import Config
from prompts.mode_selection_prompt import MODE_SELECTION_PROMPT
from prompts.rag_eligibility_checker_prompt import RAG_ELIGIBILITY_PROMPT
from prompts.csv_agent_eligibility import CSV_AGENT_ELIGIBILITY


ROUTER_MODEL = "gpt-oss:120b-cloud"

class Router: # Mode means, agentic, grafcet or simple
    """
    Decides which processing mode the system should use based on:
    - user message
    - recent conversation history
    - retrieved RAG items (optional)
    
    Modes include:
        - grafcet (Grafcet logic prompt)
        - agentic (tool-using REAct agent)
        - normal (default chat)
    """
    def get_mode(self, message: str, history: list) -> str:
        """
        Determines if the user wants: grafcet, agentic, or normal chat.
        Uses a lightweight LLM (router model) to classify the request.

        Args:
            message (str): latest user message
            history (list): last few chat turns
            retrieved_items (list): optional RAG items for context

        Returns:
            str: "grafcet", "agentic", or "normal"
        """
        #Just taking last 3 messages in history
        def format_msg(item):
            if isinstance(item, dict):
                role = item.get('role', 'user')
                content = str(item.get('content', ''))[:140]
            elif isinstance(item, str):
                role = 'user'
                content = item[:140]
            else:
                role = 'unknown'
                content = str(item)[:140]
            return f"{role}: {content}..."
        
        history_summary = "\n".join(format_msg(m) for m in history[-3:]) or "No history."

        # directly hit ollama
        payload = {
            "model": ROUTER_MODEL, # or tiny fast model
            "messages": [
                {"role": "user", "content": MODE_SELECTION_PROMPT.format(
                    history_summary=history_summary,
                    message=message,
                )}
            ],
            "stream": False,
            "options": {"temperature": 0.0}
        }

        try:
            r = requests.post(f"{Config.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=600)
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
        
    def check_pdf_rag_eligibility(self, message: str, history: list, retrieved_items) -> bool:
        """
        Determines whether to enable PDF RAG processing using LLM‑based reasoning.

        Uses a lightweight classifier prompt to decide:
            - TRUE: use RAG
            - FALSE: fallback to normal chat

        Args:
            message (str): user message
            history (list): conversation history
            retrieved_items (list): retrieved vector DB chunks

        Returns:
            bool: Whether RAG should be used
        """

        #Just taking last 3 messages in history
        history_summary = "\n".join( f"{m.get('role', 'user')}: {m.get('content', '')[:140]}..." for m in history[-3:] ) or "No history."
        retrieved_items_str = build_context(retrieved_items)

        payload = {
            "model": ROUTER_MODEL, # or tiny fast model
            "messages": [
                {"role": "user", "content": RAG_ELIGIBILITY_PROMPT.format(
                    retrieved_items=retrieved_items_str,
                    history_summary=history_summary,
                    message=message
                )}
            ],
            "stream": False,
            "options": {"temperature": 0.0}
        }

        try:
            r = requests.post(f"{Config.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=600)
            r.raise_for_status() # Break if HTTP failed
            text = r.json()["message"]["content"].strip()
            return boolean_filter(text)
        
        except Exception as e:
            print(f"Router error: {e}") # For now
            return False
        
    def should_use_csv(self, message, model, conversation_history):
        """
        Checks whether a user query should be routed to the CSV agent.

        LLM-based classifier that determines if the query is data-analysis related.

        Args:
            message (str): user query
            model (str): LLM model name
            conversation_history (list): chat history

        Returns:
            bool: True if CSV agent is recommended
        """
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
            r = requests.post(f"{Config.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=600)
            r.raise_for_status() # Break if HTTP failed
            text = r.json()["message"]["content"].strip()
            result = boolean_filter(text)
            return result if isinstance(result, bool) else False

        except Exception as e:
            print(f"Router error: {e}") # For now
            return False