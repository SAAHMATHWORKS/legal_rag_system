#!/usr/bin/env python3
"""
Enhanced Main entry point using the improved PostgresCheckpointer
Multi-Country Legal RAG System for Benin and Madagascar
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from config.settings import settings
from database.mongodb_client import MongoDBClient
from database.postgres_checkpointer import PostgresCheckpointer
from core.router import CountryRouter
from core.retriever import LegalRetriever
from core.graph_builder import GraphBuilder
from core.chat_manager import LegalChatManager
from utils.logger import setup_logging


class MultiCountryLegalRAGSystem:
    """Main system class using enhanced PostgresCheckpointer"""
    
    def __init__(self):
        self.mongo_client = MongoDBClient()
        self.postgres_checkpointer = PostgresCheckpointer(
            database_url=settings.DATABASE_URL,
            max_connections=10,
            min_connections=2
        )
        self.router = None
        self.benin_retriever = None
        self.madagascar_retriever = None
        self.llm = None
        self.graph = None
        self.chat_manager = None
        self.initialized = False

    async def initialize(self) -> bool:
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
                logging.warning("PostgreSQL initialization failed, but system may continue with fallback")
            
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
            
            # Build graph using the checkpointer from our enhanced class
            graph_builder = GraphBuilder(
                router=self.router,
                benin_retriever=self.benin_retriever,
                madagascar_retriever=self.madagascar_retriever,
                llm=self.llm,
                checkpointer=self.postgres_checkpointer.get_checkpointer()
            )
            
            workflow = graph_builder.build_graph()
            self.graph = workflow.compile(
                checkpointer=self.postgres_checkpointer.get_checkpointer()
            )
            
            # Initialize chat manager
            self.chat_manager = LegalChatManager(
                self.graph, 
                self.postgres_checkpointer.get_checkpointer()
            )
            
            # Perform health check
            await self._perform_health_check()
            
            self.initialized = True
            logging.info("✅ Multi-Country Legal RAG System initialized successfully")
            
            # Print system info
            self._print_system_info()
            
            return True
            
        except Exception as e:
            logging.error(f"❌ System initialization failed: {e}")
            return False

    async def _perform_health_check(self):
        """Perform health check after initialization"""
        try:
            health_status = await self.health_check()
            logging.info(f"🔍 System Health Status: {health_status}")
            
            # Log any unhealthy components
            unhealthy_components = [k for k, v in health_status.get('components', {}).items() if not v]
            if unhealthy_components:
                logging.warning(f"⚠️ Unhealthy components: {unhealthy_components}")
                
        except Exception as e:
            logging.warning(f"⚠️ Health check failed: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        health_status = {
            "system_initialized": self.initialized,
            "mongodb_connected": self.mongo_client.client is not None,
            "postgres_healthy": {},
            "components": {
                "router": self.router is not None,
                "benin_retriever": self.benin_retriever is not None,
                "madagascar_retriever": self.madagascar_retriever is not None,
                "llm": self.llm is not None,
                "graph": self.graph is not None,
                "chat_manager": self.chat_manager is not None
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Check PostgreSQL health
        if hasattr(self.postgres_checkpointer, 'health_check'):
            health_status["postgres_healthy"] = await self.postgres_checkpointer.health_check()
        
        return health_status

    async def chat(self, message: str, session_id: str = None, context: dict = None) -> str:
        """Public chat interface with validation"""
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        # Input validation
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
        
        # Validate context structure
        if context and not isinstance(context, dict):
            logging.warning("Invalid context provided, using default")
            context = None
            
        # Ensure context has required fields
        ctx = context or {
            "jurisdiction": "Bénin", 
            "user_type": "general", 
            "document_type": "legal"
        }
        ctx.setdefault("jurisdiction", "Bénin")
        ctx.setdefault("user_type", "general")
        ctx.setdefault("document_type", "legal")
        
        session_id = session_id or f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return await self.chat_manager.chat(message, session_id, ctx)

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a specific session"""
        if not self.initialized:
            raise RuntimeError("System not initialized")
        
        return self.chat_manager.get_session_stats(session_id)

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global system statistics"""
        if not self.initialized:
            raise RuntimeError("System not initialized")
        
        return self.chat_manager.get_global_stats()

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.mongo_client:
                self.mongo_client.close()
            
            if self.postgres_checkpointer:
                await self.postgres_checkpointer.close()
            
            logging.info("✅ System cleanup completed")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    def _print_system_info(self):
        """Print system configuration information"""
        print("\n" + "="*60)
        print("🎯 MULTI-COUNTRY LEGAL RAG SYSTEM")
        print("="*60)
        print(f"📍 Supported Jurisdictions: Bénin, Madagascar")
        print(f"🤖 AI Model: {settings.CHAT_MODEL}")
        print(f"📊 Database: MongoDB + Enhanced PostgresCheckpointer")
        print(f"🔍 Vector Search: {settings.EMBEDDING_MODEL}")
        print(f"💾 Checkpointer: Custom (with fallback support)")
        print(f"🌡️  Temperature: {settings.CHAT_TEMPERATURE}")
        print(f"📝 Max Tokens: {settings.CHAT_MAX_TOKENS}")
        print("="*60)


class TestRunner:
    """Comprehensive test runner for the legal RAG system"""
    
    def __init__(self, system: MultiCountryLegalRAGSystem):
        self.system = system
        self.results = []
        self.session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def run_test_scenario(self, category: str, test_name: str, query: str, expected: str) -> Dict[str, Any]:
        """Run a single test scenario"""
        print(f"\n🧪 [{category}] {test_name}")
        print(f"   Query: {query}")
        print(f"   Expected: {expected}")
        print("-" * 80)
        
        start_time = time.time()
        
        try:
            response = await self.system.chat(query, self.session_id)
            response_time = time.time() - start_time
            
            result = {
                "category": category,
                "test_name": test_name,
                "query": query,
                "expected": expected,
                "response": response,
                "response_time": response_time,
                "status": "✅ PASS" if self._evaluate_test(response, expected) else "❌ FAIL",
                "error": None
            }
            
            print(f"   Response: {response[:200]}{'...' if len(response) > 200 else ''}")
            print(f"   Time: {response_time:.2f}s | Status: {result['status']}")
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            error_result = {
                "category": category,
                "test_name": test_name,
                "query": query,
                "expected": expected,
                "response": f"ERROR: {str(e)}",
                "response_time": response_time,
                "status": "❌ ERROR",
                "error": str(e)
            }
            
            print(f"   Response: ERROR - {str(e)}")
            print(f"   Time: {response_time:.2f}s | Status: {error_result['status']}")
            
            return error_result
    
    def _evaluate_test(self, response: str, expected: str) -> bool:
        """Enhanced test evaluation"""
        if not response:
            return False
        
        response_lower = response.lower()
        
        # Check for error indicators
        error_indicators = ["erreur", "error", "désolé", "sorry", "impossible", "unable"]
        if any(indicator in response_lower for indicator in error_indicators):
            return False
        
        # Check if response contains meaningful content
        if len(response.strip()) < 10:
            return False
            
        return True
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["status"] == "✅ PASS"])
        failed_tests = len([r for r in self.results if r["status"] == "❌ FAIL"])
        error_tests = len([r for r in self.results if r["status"] == "❌ ERROR"])
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"🚨 Errors: {error_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Show failed tests
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.results:
                if result["status"] == "❌ FAIL":
                    print(f"  - {result['test_name']}: '{result['query']}'")
        
        # Show error tests
        if error_tests > 0:
            print(f"\n🚨 Error Tests:")
            for result in self.results:
                if result["status"] == "❌ ERROR":
                    print(f"  - {result['test_name']}: {result['error']}")
        
        # Performance statistics
        if self.results:
            response_times = [r["response_time"] for r in self.results]
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print(f"\n⏱️  Performance:")
            print(f"  Average Response Time: {avg_time:.2f}s")
            print(f"  Min Response Time: {min_time:.2f}s")
            print(f"  Max Response Time: {max_time:.2f}s")
            
            # Show slowest tests
            slow_tests = sorted(self.results, key=lambda x: x["response_time"], reverse=True)[:3]
            print(f"\n🐌 Slowest Tests:")
            for test in slow_tests:
                print(f"  - {test['test_name']}: {test['response_time']:.2f}s")

    def export_results(self, filename: str = None):
        """Export test results to file"""
        if not filename:
            filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        import json
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Results exported to: {filename}")


async def run_comprehensive_tests():
    """Run comprehensive test scenarios"""
    system = MultiCountryLegalRAGSystem()
    test_runner = TestRunner(system)
    
    try:
        # Initialize system
        print("🚀 Initializing Multi-Country Legal RAG System...")
        success = await system.initialize()
        if not success:
            print("❌ System initialization failed")
            return

        print("\n🧪 STARTING COMPREHENSIVE TESTS")
        print("="*60)

        # Test scenarios organized by categories
        test_scenarios = [
            # === CONVERSATION REPAIR TESTS ===
            {
                "category": "🔧 CONVERSATION REPAIR",
                "tests": [
                    {
                        "name": "Misunderstanding Repair",
                        "query": "Vous n'avez pas compris ma question précédente",
                        "expected": "Should detect misunderstanding and provide clarification"
                    },
                    {
                        "name": "Rephrase Request", 
                        "query": "Pouvez-vous expliquer cela plus simplement ?",
                        "expected": "Should detect rephrase request and simplify previous response"
                    },
                    {
                        "name": "Clarification Request",
                        "query": "Je ne comprends pas votre réponse",
                        "expected": "Should detect need for clarification"
                    }
                ]
            },
            
            # === NORMAL LEGAL QUERIES ===
            {
                "category": "⚖️ LEGAL QUERIES", 
                "tests": [
                    {
                        "name": "Benin Family Law - Divorce",
                        "query": "Quelles sont les conditions du divorce au Bénin ?",
                        "expected": "Should route to Benin and retrieve family law information"
                    },
                    {
                        "name": "Benin Family Law - Marriage",
                        "query": "Quelles sont les conditions du mariage civil au Bénin ?",
                        "expected": "Should route to Benin and retrieve marriage information"
                    },
                    {
                        "name": "Madagascar Commercial Law",
                        "query": "Comment créer une entreprise à Madagascar ?",
                        "expected": "Should route to Madagascar and retrieve commercial law info"
                    },
                    {
                        "name": "Madagascar Labor Law",
                        "query": "Quels sont les droits des travailleurs à Madagascar ?",
                        "expected": "Should route to Madagascar and retrieve labor law info"
                    },
                    {
                        "name": "Unclear Country Context",
                        "query": "Quels sont les droits des employés ?",
                        "expected": "Should ask for country clarification"
                    }
                ]
            },
            
            # === ASSISTANCE REQUESTS ===
            {
                "category": "🆘 HUMAN ASSISTANCE",
                "tests": [
                    {
                        "name": "Lawyer Request with Benin Context",
                        "query": "J'ai besoin d'un avocat pour mon divorce au Bénin",
                        "expected": "Should detect assistance request and ask for email"
                    },
                    {
                        "name": "Lawyer Request with Madagascar Context",
                        "query": "Je veux parler à un avocat spécialisé à Madagascar",
                        "expected": "Should detect assistance request and ask for email"
                    },
                    {
                        "name": "Generic Help Request",
                        "query": "Je veux parler à un humain",
                        "expected": "Should detect assistance but may ask for clarification"
                    },
                    {
                        "name": "Email in Query",
                        "query": "Contactez-moi à test@example.com pour une consultation",
                        "expected": "Should detect email and process assistance request"
                    }
                ]
            },
            
            # === MIXED & COMPLEX SCENARIOS ===
            {
                "category": "🔄 COMPLEX SCENARIOS",
                "tests": [
                    {
                        "name": "Follow-up Legal Question",
                        "query": "Et concernant la garde des enfants dans ce cas ?",
                        "expected": "Should maintain context from previous legal query"
                    },
                    {
                        "name": "Country Switch",
                        "query": "Et à Madagascar, comment ça se passe pour le divorce ?",
                        "expected": "Should switch country context appropriately"
                    },
                    {
                        "name": "Mixed Repair + Legal",
                        "query": "Je n'ai pas compris, pouvez-vous réexpliquer les lois sur l'héritage au Bénin ?",
                        "expected": "Should handle both repair and legal query"
                    }
                ]
            },
            
            # === EDGE CASES ===
            {
                "category": "⚠️ EDGE CASES",
                "tests": [
                    {
                        "name": "Empty Query",
                        "query": "",
                        "expected": "Should handle empty input gracefully"
                    },
                    {
                        "name": "Very Short Query",
                        "query": "loi",
                        "expected": "Should ask for clarification"
                    },
                    {
                        "name": "Non-Legal Query",
                        "query": "Quel temps fait-il aujourd'hui ?",
                        "expected": "Should handle non-legal queries appropriately"
                    }
                ]
            }
        ]

        # Run all test scenarios
        for scenario in test_scenarios:
            category = scenario["category"]
            print(f"\n{category}")
            print("="*50)
            
            for test in scenario["tests"]:
                result = await test_runner.run_test_scenario(
                    category, test["name"], test["query"], test["expected"]
                )
                test_runner.results.append(result)
                
                # Small delay between tests to avoid rate limiting
                await asyncio.sleep(1)

        # Print final summary
        test_runner.print_summary()
        
        # Show system statistics
        stats = system.get_global_stats()
        print(f"\n📈 SYSTEM STATISTICS:")
        print(f"  Total Queries: {stats['total_queries']}")
        print(f"  Benin Routes: {stats['routing_stats']['benin']}")
        print(f"  Madagascar Routes: {stats['routing_stats']['madagascar']}")
        print(f"  Unclear Routes: {stats['routing_stats']['unclear']}")
        print(f"  Active Sessions: {stats['active_sessions']}")
        
        # Export results
        test_runner.export_results()

    except Exception as e:
        logging.error(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await system.cleanup()


async def interactive_mode():
    """Run interactive chat mode"""
    system = MultiCountryLegalRAGSystem()
    
    try:
        print("🚀 Initializing Multi-Country Legal RAG System...")
        success = await system.initialize()
        if not success:
            print("❌ System initialization failed")
            return

        print("\n💬 INTERACTIVE MODE")
        print("Type 'quit' to exit, 'stats' for statistics, 'health' for health check")
        print("="*50)
        
        session_id = f"interactive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"Session ID: {session_id}")
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif user_input.lower() == 'stats':
                    stats = system.get_global_stats()
                    print(f"\n📊 Current Stats:")
                    print(f"  Total Queries: {stats['total_queries']}")
                    print(f"  Benin: {stats['routing_stats']['benin']}")
                    print(f"  Madagascar: {stats['routing_stats']['madagascar']}")
                    print(f"  Unclear: {stats['routing_stats']['unclear']}")
                    print(f"  Active Sessions: {stats['active_sessions']}")
                    continue
                elif user_input.lower() == 'health':
                    health = await system.health_check()
                    print(f"\n❤️  System Health:")
                    print(f"  Initialized: {health['system_initialized']}")
                    print(f"  MongoDB: {'✅ Connected' if health['mongodb_connected'] else '❌ Disconnected'}")
                    print(f"  PostgreSQL: {health['postgres_healthy']}")
                    print(f"  Components: {health['components']}")
                    continue
                elif not user_input:
                    print("⚠️  Please enter a message")
                    continue
                
                start_time = time.time()
                response = await system.chat(user_input, session_id)
                response_time = time.time() - start_time
                
                print(f"🤖 Assistant ({response_time:.2f}s): {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                
    finally:
        await system.cleanup()


async def health_check_mode():
    """Run system health check only"""
    system = MultiCountryLegalRAGSystem()
    
    try:
        print("🔍 Performing System Health Check...")
        success = await system.initialize()
        
        if success:
            health = await system.health_check()
            print("\n" + "="*50)
            print("❤️  SYSTEM HEALTH REPORT")
            print("="*50)
            print(f"✅ System Initialized: {health['system_initialized']}")
            print(f"📊 MongoDB: {'✅ Connected' if health['mongodb_connected'] else '❌ Disconnected'}")
            print(f"🗄️  PostgreSQL: {health['postgres_healthy']}")
            print(f"🕐 Timestamp: {health['timestamp']}")
            
            print("\n🔧 Components Status:")
            for component, status in health['components'].items():
                print(f"  {component}: {'✅ OK' if status else '❌ Missing'}")
                
        else:
            print("❌ System initialization failed")
            
    finally:
        await system.cleanup()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Multi-Country Legal RAG System for Benin and Madagascar",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode test          # Run comprehensive tests
  %(prog)s --mode interactive   # Start interactive chat
  %(prog)s --mode health        # Perform health check only
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["test", "interactive", "health"], 
        default="test",
        help="Run mode: test (comprehensive tests), interactive (chat mode), or health (system health check)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "test":
        asyncio.run(run_comprehensive_tests())
    elif args.mode == "interactive":
        asyncio.run(interactive_mode())
    elif args.mode == "health":
        asyncio.run(health_check_mode())