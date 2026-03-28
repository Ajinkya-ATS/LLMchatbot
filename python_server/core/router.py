from utils.response_cleaner import mode_selection, boolean_filter
from utils.basic_utils import build_context
from utils.ollama_utils import _call_ollama
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

        prompt = MODE_SELECTION_PROMPT.format(
            history_summary=history_summary,
            message=message,
        )

        result = _call_ollama(
            model=ROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            mode="router"
        )

        if isinstance(result, dict) and "error" in result:
            print(f"Router error: {result['error']}")
            return "normal"

        text = result["response"].strip()
        match = mode_selection(text)
        return match if match is not None else "normal"
        
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

        prompt = RAG_ELIGIBILITY_PROMPT.format(
            retrieved_items=retrieved_items_str,
            history_summary=history_summary,
            message=message
        )

        result = _call_ollama(
            model=ROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            mode="rag_router"
        )

        if isinstance(result, dict) and "error" in result:
            print(f"RAG eligibility router error: {result['error']}")
            return False

        text = result["response"].strip()
        return boolean_filter(text)
        
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

        prompt = CSV_AGENT_ELIGIBILITY.format(
            query=message,
            history=history_summary
        )

        result = _call_ollama(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            mode="csv_router"
        )

        if isinstance(result, dict) and "error" in result:
            print(f"CSV router error: {result['error']}")
            return False

        text = result["response"].strip()
        result_bool = boolean_filter(text)
        return result_bool if isinstance(result_bool, bool) else False