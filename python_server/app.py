from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)  # equivalent to app.use(cors())

PORT = int(os.getenv("PORT", 5001))

# Ollama API base URL
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

AVAILABLE_MODELS = [
    {
        "id": "gpt-oss-20b",
        "name": "gpt-oss:20b",
        "size": "13 GB",
        "modified": "1 day ago",
        "description": "GPT-OSS 20B model - Large open source language model"
    },
    {
        "id": "15cb39fd9394",
        "name": "gemma3n:e4b",
        "size": "7.5 GB",
        "modified": "6 weeks ago",
        "description": "Google Gemma 3N model with enhanced capabilities"
    },
    {
        "id": "dae161e27b0e",
        "name": "qwen2.5-coder:7b",
        "size": "4.7 GB",
        "modified": "2 months ago",
        "description": "Qwen2.5 Coder model optimized for programming tasks"
    },
    {
        "id": "6995872bfe4c",
        "name": "deepseek-r1:8b",
        "size": "5.2 GB",
        "modified": "2 months ago",
        "description": "DeepSeek R1 model with reasoning capabilities"
    },
    {
        "id": "f974a74358d6",
        "name": "mistral:latest",
        "size": "4.1 GB",
        "modified": "3 months ago",
        "description": "Mistral latest model for general purpose tasks"
    }
]


@app.route('/api/models', methods=['GET'])
def get_models():
    return jsonify(AVAILABLE_MODELS)


@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        data = r.json()
        return jsonify({
            "status": "connected",
            "ollamaVersion": data.get("version", "unknown"),
            "availableModels": data.get("models", [])
        })
    except requests.RequestException as e:
        return jsonify({
            "status": "disconnected",
            "error": "Cannot connect to Ollama. Please ensure Ollama is running on localhost:11434"
        }), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message')
    model = data.get('model')
    conversation_history = data.get('conversationHistory', [])

    if not message or not model:
        return jsonify({"error": "Message and model are required"}), 400

    try:
        system_prompt = {
            "role": "system",
            "content": (
                "You are a helpful AI assistant. Respond naturally and conversationally, "
                "like a human would in a casual chat. Keep responses concise, friendly, "
                "and conversational. Avoid excessive formatting, numbered lists, bullet points, "
                "or markdown unless specifically requested. Just talk naturally like you would "
                "to a friend."
            )
        }

        messages = [
            system_prompt,
            *conversation_history,
            {"role": "user", "content": message}
        ]

        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False
            },
            timeout=120  # 2 minutes
        )
        resp.raise_for_status()

        ollama_response = resp.json()
        clean_response = ollama_response.get("message", {}).get("content", "")

        # Clean up response - same logic as in JS
        import re
        clean_response = re.sub(r'^(Assistant:|AI:|Bot:)\s*', '', clean_response, flags=re.IGNORECASE)
        clean_response = re.sub(
            r'^(I am an AI|I am an artificial intelligence).*?How can I help you today\?',
            '', clean_response, flags=re.IGNORECASE
        )
        clean_response = re.sub(r'\n\d+\.\s*', '\n• ', clean_response)
        clean_response = re.sub(r'^\d+\.\s*', '• ', clean_response, flags=re.MULTILINE)
        clean_response = re.sub(r'\n{3,}', '\n\n', clean_response)
        clean_response = clean_response.strip()

        return jsonify({
            "response": clean_response,
            "model": model,
            "timestamp": datetime.utcnow().isoformat()
        })

    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "Cannot connect to Ollama. Please ensure Ollama is running and the model is available."
        }), 500
    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 404:
            return jsonify({
                "error": f"Model '{model}' not found. Please ensure the model is installed in Ollama."
            }), 404
        else:
            return jsonify({
                "error": http_err.response.json().get("error", "Ollama returned an error")
            }), 500
    except Exception as e:
        print("Chat error:", str(e))
        return jsonify({"error": "An error occurred while processing your request."}), 500


@app.route('/api/models/pull', methods=['POST'])
def pull_model():
    data = request.get_json()
    model_name = data.get('modelName')

    if not model_name:
        return jsonify({"error": "Model name is required"}), 400

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": model_name, "stream": False},
            timeout=600  # long timeout for pulling large models
        )
        resp.raise_for_status()

        return jsonify({
            "success": True,
            "message": f"Model {model_name} pulled successfully",
            "details": resp.json()
        })

    except Exception as e:
        print("Pull model error:", str(e))
        error_msg = getattr(e.response, 'json', lambda: {}).get("error", "Failed to pull model")
        return jsonify({"error": error_msg}), 500


if __name__ == '__main__':
    print(f"Server running on port {PORT}")
    print(f"Ollama base URL: {OLLAMA_BASE_URL}")
    app.run(host='0.0.0.0', port=PORT, debug=False)