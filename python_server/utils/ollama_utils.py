from config import Config
import requests
from utils.response_cleaner import clean_response
from utils.basic_utils import formatted_datetime

def _call_ollama(model: str, messages: list, temperature: float = 0.0, mode: str = "normal"):
    """
    Makes API call to Ollama model server for chat completion.
    Includes error handling for timeouts, HTTP errors, etc.
    """
    try:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }

        resp = requests.post(
            f"{Config.OLLAMA_BASE_URL}/api/chat",
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
    
def _build_messages(system_prompt: str, history: list, user_message: str) -> list:
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