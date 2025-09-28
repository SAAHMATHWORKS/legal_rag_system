#!/usr/bin/env python3
"""
Main entry point for the Multi-Country Legal RAG System
"""

import asyncio
import logging
from datetime import datetime

from config.settings import settings
from database.mongodb_client import MongoDBClient
from database.postgres_checkpointer import PostgresCheckpointer
from core.router import CountryRouter
from core.retriever import LegalRetriever
from core.graph_builder import GraphBuilder
from core.chat_manager import LegalChatManager
from utils.logger import setup_logging
from interfaces.web_interface import LegalRAGAPI

class MultiCountryLegalRAGSystem:
    """Main system class that orchestrates all components"""
    
    def __init__(self):
        self.mongo_client = MongoDBClient()
        self.postgres_checkpointer = PostgresCheckpointer()
        self.router = None
        self.benin_retriever = None
        self.madagascar_retriever = None
        self.llm = None
        self.graph = None
        self.chat_manager = None
        self.initialized = False

    async def initialize(self):
        """Initialize the complete system"""
        try:
            # Setup logging
            setup_logging()
            
            # Validate settings
            settings.validate()
            
            # Initialize databases
            if not self.mongo_client.connect():
                raise Exception("MongoDB connection failed")
                
            if not await self.postgres_checkpointer.initialize():
                raise Exception("PostgreSQL initialization failed")
            
            # Initialize core components
            self.router = CountryRouter()
            
            self.benin_retriever = LegalRetriever(
                self.mongo_client.benin_vectorstore,
                self.mongo_client.benin_collection
            )
            
            self.madagascar_retriever = LegalRetriever(
                self.mongo_client.madagascar_vectorstore,
                self.mongo_client.madagascar_collection
            )
            
            # Initialize LLM
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=settings.CHAT_MODEL,
                temperature=settings.CHAT_TEMPERATURE,
                max_tokens=settings.CHAT_MAX_TOKENS
            )
            
            # Build graph
            graph_builder = GraphBuilder(
                router=self.router,
                benin_retriever=self.benin_retriever,
                madagascar_retriever=self.madagascar_retriever,
                llm=self.llm,
                checkpointer=self.postgres_checkpointer.checkpointer
            )
            
            workflow = graph_builder.build_graph()
            self.graph = workflow.compile(checkpointer=self.postgres_checkpointer.checkpointer)
            
            # Initialize chat manager
            self.chat_manager = LegalChatManager(self.graph, self.postgres_checkpointer.checkpointer)
            
            self.initialized = True
            logging.info("✅ Multi-Country Legal RAG System initialized successfully")
            
            # Print system info
            self._print_system_info()
            
            return True
            
        except Exception as e:
            logging.error(f"❌ System initialization failed: {e}")
            return False

    async def chat(self, message: str, session_id: str = None, context: dict = None):
        """Public chat interface"""
        if not self.initialized:
            raise RuntimeError("System not initialized")
        
        session_id = session_id or f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return await self.chat_manager.chat(message, session_id, context)

    async def cleanup(self):
        """Cleanup resources"""
        if self.mongo_client:
            self.mongo_client.close()
        
        if self.postgres_checkpointer:
            await self.postgres_checkpointer.close()
        
        logging.info("✅ System cleanup completed")

    def _print_system_info(self):
        """Print system configuration information"""
        print("\n" + "="*60)
        print("🎯 MULTI-COUNTRY LEGAL RAG SYSTEM")
        print("="*60)
        print(f"📍 Supported Jurisdictions: Bénin, Madagascar")
        print(f"🤖 AI Model: {settings.CHAT_MODEL}")
        print(f"📊 Database: MongoDB + PostgreSQL")
        print(f"🔍 Vector Search: {settings.EMBEDDING_MODEL}")
        print("="*60)

# CLI interface for testing
async def main():
    """Main function for CLI testing"""
    system = MultiCountryLegalRAGSystem()
    
    try:
        # Initialize system
        success = await system.initialize()
        if not success:
            print("❌ System initialization failed")
            return

        # Test conversation - UPDATED TEST QUERIES
        session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        test_queries = [
            # Test 1: Conversation repair (misunderstanding)
            "Vous n'avez pas compris ce que je demande",
            
            # Test 2: Normal legal query with country
            "Quelles sont les lois sur le divorce au Bénin ?",
            
            # Test 3: Assistance request
            "Je souhaite parler à un avocat humain concernant mon divorce",
            
            # Test 4: Another repair (rephrase request)
            "Pouvez-vous reformuler votre réponse plus simplement ?",
            
        ]

        for i, query in enumerate(test_queries, 1):
            print(f"\n{'='*60}")
            print(f"TEST {i}: {query}")
            print(f"{'='*60}")
            print(f"👤 User: {query}")
            response = await system.chat(query, session_id)
            print(f"🤖 Assistant: {response}")
            print("-" * 80)
            
            # Small delay between queries
            await asyncio.sleep(1)

        # Show statistics
        stats = system.chat_manager.get_global_stats()
        print(f"\n📊 Session Statistics:")
        print(f"   - Total queries: {stats['total_queries']}")
        print(f"   - Benin routes: {stats['routing_stats']['benin']}")
        print(f"   - Madagascar routes: {stats['routing_stats']['madagascar']}")
        print(f"   - Unclear routes: {stats['routing_stats']['unclear']}")

    except Exception as e:
        logging.error(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await system.cleanup()

if __name__ == "__main__":
    asyncio.run(main())