import requests
from utils.response_cleaner import mode_selection
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config import OLLAMA_BASE_URL
from prompts.router_prompt import ROUTER_PROMPT

class ModeRouter: # Mode means, agentic, grafcet or simple
    
    @staticmethod
    def get_mode(message: str, history: list) -> str:

        #Just taking last 4 messages in history
        history_summary = "\n".join( f"{m.get('role', 'user')}: {m.get('content', '')[:140]}..." for m in history[-4:] ) or "No history."

        # directly hit ollama
        payload = {
            "model": "mistral:latest",          # or tiny fast model
            "messages": [
                {"role": "user", "content": ROUTER_PROMPT.format(
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
            match = mode_selection(text)
            if (match is not None):
                return match
            else:
                return "normal"

        except Exception as e:
            print(f"Router error: {e}") # For now
            return "normal"