import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
    
    GPT5_MODEL = "gpt-5.1-2025-11-13"
    GPT4O_MINI_MODEL = "gpt-4o-mini"
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
    
    @classmethod
    def validate(cls):
        required_vars = [
            cls.OPENAI_API_KEY,
            cls.NEO4J_URI,
            cls.NEO4J_PASSWORD
        ]
        if not all(required_vars):
            raise ValueError("Missing required environment variables")
        return True