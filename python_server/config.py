import os
from dotenv import load_dotenv
load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
PORT = int(os.getenv("PORT", 5001))

class SQLConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False # disables a feature that wastes memory
    SQLALCHEMY_ECHO = False # set True only for debugging SQL queries