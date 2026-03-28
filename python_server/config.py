import os
from dotenv import load_dotenv

class Config:
    load_dotenv()
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    PORT = int(os.getenv("PORT", 5001))

    ALLOWED_ORIGINS = [
        "http://localhost:3000",
    ]

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False