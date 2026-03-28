# app/factory.py
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from config import Config
from services.chat_service import ChatService
from services.vector_db_service import VectorStore
from models import db
from flask_migrate import Migrate
import os
from app.routes import register_routes


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
    load_dotenv()

    # Instantiate Flask app
    app = Flask(__name__)
    
    # Load configurations for sql
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object('config.Config')

    # Enable CORS for cross-origin JavaScript requests
    CORS(app, origins=app.config.get("ALLOWED_ORIGINS", "*"))

    # Initialize SQLAlchemy and migrations
    db.init_app(app)
    Migrate(app, db)

    # Initialize vector store (Qdrant + Embeddings)
    try:
        vector_store = VectorStore()
    except Exception as e:
        raise RuntimeError("Error while initializing vector store")

    if not vector_store:
        raise RuntimeError("VectorStore not initialized")
    
    app.logger.info("Vector store initialized")

    # Initialize ChatService with vector store dependency injection
    try:
        chat_service = ChatService(vector_store=vector_store)
        app.logger.info("ChatService initialized")
    except Exception as e:
        app.logger.exception("Chat Service init failed")
        raise
    # Attach services to the Flask app instance for global acces
    app.chat_service = chat_service
    app.vector_store = vector_store

    # Register all routes (API endpoints)
    register_routes(app)

    return app