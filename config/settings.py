import os
from dotenv import load_dotenv

load_dotenv("../.env", override=True)

class Settings:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MONGO_URI = os.environ.get("MONGO_URI")
    NEON_DB_URL = os.environ.get("NEON_DB_URL")
    NEON_END_POINT = os.getenv("NEON_END_POINT")
    
    # Database
    DATABASE_URL = NEON_END_POINT
    
    # Model Configurations
    EMBEDDING_MODEL = "text-embedding-ada-002"
    CHAT_MODEL = "gpt-4o-mini"
    CHAT_TEMPERATURE = 0.1
    CHAT_MAX_TOKENS = 2000
    
    # Vector Search
    VECTOR_INDEX_NAME = "vector_index"
    TEXT_KEY = "contenu"
    EMBEDDING_KEY = "vecteur_embedding"
    
    # Collections
    BENIN_COLLECTION = "legal_documents"
    MADAGASCAR_COLLECTION = "legal_documents_madagascar"
    DATABASE_NAME = "legal_db"
    
    # Search Parameters
    MAX_SEARCH_RESULTS = 10
    MAX_CONVERSATION_HISTORY = 8
    
    def validate(self):
        missing = []
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not self.MONGO_URI:
            missing.append("MONGO_URI")
        if not self.NEON_DB_URL:
            missing.append("NEON_DB_URL")
        if not self.NEON_END_POINT:
            missing.append("NEON_END_POINT")
        
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

settings = Settings()