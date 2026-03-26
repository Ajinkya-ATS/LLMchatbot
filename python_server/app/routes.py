from flask import request, jsonify
import requests
import os
import uuid
from werkzeug.utils import secure_filename
from models import UploadedFile, db
from utils.basic_utils import compute_file_hash
from config import OLLAMA_BASE_URL, PORT

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

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'csv', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def register_routes(app):

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
        result = app.chat_service.handle_chat(data)
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
            
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file_hash = compute_file_hash(file)
            # file.seek(0) # This resets the cursor which may be moved to end due to compute_file_hash
            existing_file = UploadedFile.query.filter_by(file_hash=file_hash).first()
            
            if existing_file:
                return jsonify({
                    "status": "duplicate",
                    "fileId": existing_file.file_id,
                    "fileName": existing_file.original_filename,
                    "filePath": existing_file.file_path,
                    "fileType": existing_file.file_type
                }), 200

            # Generate unique filename
            filename = secure_filename(file.filename)
            file_id = str(uuid.uuid4())
            ext = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{file_id}.{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            # Save file
            file.save(filepath)
            if not os.path.exists(filepath):
                print("File was NOT saved!")
            else:
                print("File saved successfully")

            new_file = UploadedFile(
                file_id=file_id,
                original_filename=filename,
                file_hash=file_hash,
                file_type=ext,
                file_path=filepath
            )
            db.session.add(new_file)
            db.session.commit()

            try:
                if ext == 'pdf':
                    app.vector_store.store_to_vector_db(file_id, filepath)
                    print(f"File {file_id} processed and stored in vector DB")
                elif ext == "csv":
                    pass
            except Exception as e:
                print(f"Warning: Failed to process embeddings for {file_id}: {str(e)}")
            
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
