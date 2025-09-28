from pymongo import MongoClient
from langchain_mongodb.vectorstores import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from typing import Dict, List
from config.settings import settings

class MongoDBClient:
    def __init__(self):
        self.client = None
        self.db = None
        self.benin_collection = None
        self.madagascar_collection = None
        self.benin_vectorstore = None
        self.madagascar_vectorstore = None
        self.embedding_model = None

    def connect(self):
        """Connect to MongoDB and initialize collections"""
        try:
            self.client = MongoClient(settings.MONGO_URI)
            self.db = self.client[settings.DATABASE_NAME]
            
            # Initialize collections
            self.benin_collection = self.db[settings.BENIN_COLLECTION]
            self.madagascar_collection = self.db[settings.MADAGASCAR_COLLECTION]
            
            # Initialize embedding model
            self.embedding_model = OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY
            )
            
            # Initialize vector stores
            self.benin_vectorstore = MongoDBAtlasVectorSearch(
                collection=self.benin_collection,
                embedding=self.embedding_model,
                index_name=settings.VECTOR_INDEX_NAME,
                text_key=settings.TEXT_KEY,
                embedding_key=settings.EMBEDDING_KEY,
            )
            
            self.madagascar_vectorstore = MongoDBAtlasVectorSearch(
                collection=self.madagascar_collection,
                embedding=self.embedding_model,
                index_name=settings.VECTOR_INDEX_NAME,
                text_key=settings.TEXT_KEY,
                embedding_key=settings.EMBEDDING_KEY,
            )
            
            print("✅ MongoDB connected successfully")
            return True
            
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            return False

    def get_collection_stats(self) -> Dict:
        """Get statistics for both collections"""
        if not self.client:
            return {}
        
        try:
            benin_count = self.benin_collection.count_documents({})
            madagascar_count = self.madagascar_collection.count_documents({})
            
            # Sample document to check schema
            benin_sample = self.benin_collection.find_one()
            madagascar_sample = self.madagascar_collection.find_one()
            
            return {
                "benin": {
                    "document_count": benin_count,
                    "has_embeddings": bool(benin_sample and 'vecteur_embedding' in benin_sample),
                    "sample_fields": list(benin_sample.keys()) if benin_sample else []
                },
                "madagascar": {
                    "document_count": madagascar_count,
                    "has_embeddings": bool(madagascar_sample and 'vecteur_embedding' in madagascar_sample),
                    "sample_fields": list(madagascar_sample.keys()) if madagascar_sample else []
                }
            }
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            return {}

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("✅ MongoDB connection closed")