from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
from services.chat_service import ChatService
from flask_migrate import Migrate
from services.vector_db_service import VectorStore
from config import PORT, OLLAMA_BASE_URL
import uuid
from werkzeug.utils import secure_filename
from models import UploadedFile, db
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)
CORS(app)  # equivalent to app.use(cors())

# Initialize VectorStore for embeddings
vector_store = VectorStore()
print("VectorStore initialized - Embedding models loaded")
app.config.from_object('config.SQLConfig')
db.init_app(app)
migrate = Migrate(app, db) # To enable flask db commands

AVAILABLE_MODELS = [
    {
        "id": "mistral",
        "name": "mistral-large-3:675b-cloud",
        "size": "500 GB",
        "modified": "1 day ago",
        "description": "Powerful mistral model"
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
        "name": "kimi-k2.5:cloud",
        "size": "1 TB",
        "modified": "2 months ago",
        "description": "Kimi-k2 model"
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

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'csv', 'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Create uploads folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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


@app.post('/api/chat')
def chat():
    data = request.get_json()
    result = ChatService.handle_chat(data)
    return jsonify(result)


@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Only CSV and PDF files are allowed"}), 400
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{file_id}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save file
        file.save(filepath)
        
        # Process and store embeddings if it's a PDF
        try:
            if ext == 'pdf':
                # Store to vector DB with file_id as collection name
                vector_store.store_to_vector_db(file_id, filepath)
                print(f"File {file_id} processed and stored in vector DB")
            elif ext == "csv":
                pass
        except Exception as e:
            print(f"Warning: Failed to process embeddings for {file_id}: {str(e)}")
            # Still return success for upload, just warn about embeddings
        
        return jsonify({
            "status": "success",
            "fileId": file_id,
            "fileName": filename,
            "filePath": filepath,
            "fileType": file.content_type
        }), 200
    
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({"error": str(e)}), 500


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
    # Initialize ChatService with vector store
    ChatService.vector_store = vector_store
    
    print(f"Server running on port {PORT}")
    print(f"Ollama base URL: {OLLAMA_BASE_URL}")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)