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
    app = Flask(__name__)
    
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object('config.SQLConfig')

    CORS(app)

    db.init_app(app)
    Migrate(app, db)

    vector_store = VectorStore()
    print("VectorStore initialized and Embedding models loaded")

    chat_service = ChatService(vector_store=vector_store)
    print("ChatService initialized")

    app.chat_service = chat_service
    app.vector_store = vector_store
    app.PORT = PORT
    app.OLLAMA_BASE_URL = OLLAMA_BASE_URL

    register_routes(app)

    return app