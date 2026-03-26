# app/factory.py
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from config import PORT, OLLAMA_BASE_URL
from services.chat_service import ChatService
from services.vector_db_service import VectorStore
from models import db
from flask_migrate import Migrate
import os
from app.routes import register_routes

load_dotenv()

def create_app(config_class=None):
    """
    Application factory function.
    Creates, configures, and returns a fully initialized Flask application.

    This follows Flask's recommended pattern for:
        - scalable apps
        - registering services
        - enabling database support
        - attaching routes
        - modular initialization

    Args:
        config_class: Optional configuration class to override default config.

    Returns:
        Flask application instance.
    """

    # Instantiate Flask app
    app = Flask(__name__)
    
    # Load configurations for sql
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object('config.SQLConfig')

    # Enable CORS for cross-origin JavaScript requests
    CORS(app)

    # Initialize SQLAlchemy and migrations
    db.init_app(app)
    Migrate(app, db)

    # Initialize vector store (Qdrant + Embeddings)
    vector_store = VectorStore()
    print("VectorStore initialized and Embedding models loaded")

    # Initialize ChatService with vector store dependency injection
    chat_service = ChatService(vector_store=vector_store)
    print("ChatService initialized")

    # Attach services to the Flask app instance for global acces
    app.chat_service = chat_service
    app.vector_store = vector_store
    app.PORT = PORT
    app.OLLAMA_BASE_URL = OLLAMA_BASE_URL

    # Register all routes (API endpoints)
    register_routes(app)

    return app