# database_diagnostic.py
import asyncio
from database.mongodb_client import MongoDBClient
from config import settings

async def check_database_content():
    client = MongoDBClient()
    if client.connect():
        print("🔍 Checking database content...")
        
        # Check collections exist
        collections = client.db.list_collection_names()
        print(f"📂 Collections: {collections}")
        
        # Check document counts
        stats = client.get_collection_stats()
        print(f"📊 Collection stats: {stats}")
        
        # Check if vector index exists
        try:
            indexes = client.db[settings.BENIN_COLLECTION].list_indexes()
            print("🔍 Benin collection indexes:")
            for idx in indexes:
                print(f"  - {idx}")
        except Exception as e:
            print(f"❌ Error checking indexes: {e}")
        
        client.close()

if __name__ == "__main__":
    asyncio.run(check_database_content())