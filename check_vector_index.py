# check_vector_index.py
from pymongo import MongoClient
from config.settings import settings

def check_vector_index():
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.DATABASE_NAME]
    collection = db[settings.BENIN_COLLECTION]

    try:
        # 1. Check for classical indexes
        print("🔍 Standard indexes:")
        for idx in collection.list_indexes():
            print(f"  - {idx['name']}: {idx.get('key', {})}")

        # 2. Check for Atlas vector search indexes
        print("\n🔍 Vector Search indexes:")
        try:
            for vs_index in collection.list_search_indexes():
                print(f"  - {vs_index['name']}: {vs_index}")
        except Exception as e:
            print("⚠️ Could not fetch vector search indexes. "
                  "Are you sure you're using MongoDB Atlas Search / MongoDB 7.0+?")
            print(f"   Details: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_vector_index()
