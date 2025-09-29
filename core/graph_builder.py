from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.runnables import RunnableConfig
from typing import List, Dict, Any, Optional, Annotated, Literal
import logging
import time
from datetime import datetime

from models.state_models import MultiCountryLegalState
from core.router import CountryRouter
from core.retriever import LegalRetriever
from core.assistance_node import AssistanceNode
from core.conversation_repair import ConversationRepair 

from utils.helpers import dict_to_message_obj, message_obj_to_dict

logger = logging.getLogger(__name__)

class GraphBuilder:
    def __init__(self, router: CountryRouter, benin_retriever: LegalRetriever, 
                 madagascar_retriever: LegalRetriever, llm, checkpointer: AsyncPostgresSaver):
        self.router = router
        self.benin_retriever = benin_retriever
        self.madagascar_retriever = madagascar_retriever
        self.assistance_node = AssistanceNode()
        self.conversation_repair = ConversationRepair()
        self.llm = llm
        self.checkpointer = checkpointer

    def build_graph(self) -> StateGraph:
        """Build the complete state graph for multi-country legal RAG system"""
        workflow = StateGraph(MultiCountryLegalState)
        
        # Add nodes
        workflow.add_node("conversation_repair", self._conversation_repair_node)
        workflow.add_node("router", self._router_node)
        workflow.add_node("benin_retrieval", self._benin_retrieval_node)
        workflow.add_node("madagascar_retrieval", self._madagascar_retrieval_node)
        workflow.add_node("unclear_route", self._unclear_route_node)
        workflow.add_node("response_generation", self._response_generation_node)
        workflow.add_node("detect_assistance", self._detect_assistance_node)
        workflow.add_node("collect_email", self._collect_email_node)
        workflow.add_node("process_assistance", self._process_assistance_node)
        
        # Modified edges - CHECK REPAIR FIRST
        workflow.add_edge(START, "conversation_repair")
        workflow.add_conditional_edges("conversation_repair", self._route_after_repair_check)
        workflow.add_conditional_edges("router", self._route_by_country)
        workflow.add_edge("benin_retrieval", "detect_assistance")
        workflow.add_edge("madagascar_retrieval", "detect_assistance")
        workflow.add_edge("unclear_route", "detect_assistance")
        
        # Rest of the edges
        workflow.add_conditional_edges(
            "detect_assistance", 
            self._route_after_detection,
            {
                "collect_email": "collect_email",
                "response_generation": "response_generation",
                "process_assistance": "process_assistance"
            }
        )
        
        workflow.add_edge("collect_email", "process_assistance")
        workflow.add_edge("process_assistance", END)
        workflow.add_edge("response_generation", END)
        
        logger.info("✅ Multi-country legal RAG graph built successfully")
        return workflow

    # === CONVERSATION REPAIR NODE ===
    async def _conversation_repair_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> Dict[str, Any]:
        """Handle conversation repair and meta-communication"""
        try:
            s = state.model_dump()
            
            last_human = self._get_last_human_message(s.get("messages", []))
            if not last_human:
                logger.debug("No human message found for repair check")
                return {"repair_type": None, "messages": []}
            
            user_query = last_human.get("content", "").strip()
            if not user_query:
                logger.debug("Empty user query found")
                return {"repair_type": None, "messages": []}
            
            logger.debug(f"Checking repair intent for: '{user_query[:50]}...'")
            repair_type = self.conversation_repair.detect_repair_intent(user_query, s.get("messages", []))
            logger.debug(f"Detected repair type: {repair_type}")
            
            if repair_type:
                repair_response = self.conversation_repair.generate_repair_response(repair_type, s.get("messages", []))
                logger.info(f"Generated repair response for type '{repair_type}': {repair_response[:100]}...")
                return {
                    "repair_type": repair_type,
                    "messages": [{
                        "role": "assistant",
                        "content": repair_response,
                        "meta": {
                            "is_repair_response": True,
                            "repair_type": repair_type,
                            "timestamp": self._get_timestamp()
                        }
                    }]
                }
            
            return {"repair_type": None, "messages": []}
            
        except Exception as e:
            logger.error(f"Error in conversation repair: {str(e)}")
            return {"repair_type": None, "messages": []}

    # === ROUTING NODES ===
    async def _router_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> dict:
        """Route queries to appropriate country system"""
        try:
            s = state.model_dump()
            
            # Enhanced state validation
            if not s.get("messages"):
                logger.warning("No messages in state for router")
                return self._create_router_response("unclear", "No messages in state", s.get("legal_context", {}))
                
            last_human = self._get_last_human_message(s.get("messages", []))
            if not last_human:
                logger.warning("No user query found in router")
                return self._create_router_response("unclear", "No user query found", s.get("legal_context", {}))

            user_query = last_human.get("content", "").strip()
            if not user_query:
                logger.warning("Empty user query in router")
                return self._create_router_response("unclear", "Empty user query", s.get("legal_context", {}))
            
            logger.info(f"Routing query: '{user_query[:50]}...'")
            routing_result = await self.router.route_query(user_query, s["messages"])
            updated_context = self._update_legal_context(s["legal_context"], routing_result.country)
            
            logger.info(f"Router decision: {routing_result.country} ({routing_result.confidence}) - {routing_result.method}")
            
            return {
                "router_decision": routing_result.country,
                "route_explanation": f"{routing_result.method}: {routing_result.explanation}",
                "legal_context": updated_context
            }
            
        except Exception as e:
            logger.error(f"Router error: {str(e)}")
            legal_context = state.legal_context if hasattr(state, 'legal_context') else {}
            return self._create_router_response("unclear", f"Router error: {str(e)}", legal_context)

    async def _benin_retrieval_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> dict:
        """Retrieve context from Benin legal database"""
        return await self._country_retrieval_node(state, "benin", self.benin_retriever)

    async def _madagascar_retrieval_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> dict:
        """Retrieve context from Madagascar legal database"""
        return await self._country_retrieval_node(state, "madagascar", self.madagascar_retriever)

    async def _country_retrieval_node(self, state: MultiCountryLegalState, country: str, retriever: LegalRetriever) -> dict:
        """Generic country retrieval implementation with error handling"""
        try:
            s = state.model_dump()
            last_human = self._get_last_human_message(s.get("messages", []))
            
            if not last_human:
                logger.warning(f"No query for {country} retrieval")
                return {"search_results": f"No query for {country} retrieval", "detected_articles": []}

            user_query = last_human.get("content", "").strip()
            if not user_query:
                logger.warning(f"Empty query for {country} retrieval")
                return {"search_results": f"Empty query for {country} retrieval", "detected_articles": []}
            
            logger.info(f"Performing {country} retrieval for: '{user_query[:50]}...'")
            
            # Use async version
            enhanced_docs, detected_articles, applied_filters, supplemental_message = await retriever.smart_legal_query(user_query, country)
            
            search_results = retriever.format_search_results(
                user_query, enhanced_docs, detected_articles, applied_filters, country, supplemental_message
            )
            
            logger.info(f"Retrieved {len(enhanced_docs)} documents for {country}, detected {len(detected_articles)} articles")
            
            return {
                "search_results": search_results,
                "detected_articles": detected_articles,
                "last_search_query": user_query,
                "_debug": {
                    "enhanced_docs_count": len(enhanced_docs),
                    "applied_filters": applied_filters,
                    "supplemental_message": supplemental_message
                }
            }
            
        except Exception as e:
            logger.error(f"Error in {country} retrieval: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "search_results": f"Erreur lors de la recherche {country}: {str(e)}",
                "detected_articles": [],
                "_debug": {"error": str(e)}
            }

    async def _unclear_route_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> dict:
        """Handle unclear routing cases"""
        try:
            logger.info("Handling unclear route - requesting clarification")
            clarification_msg = {
                "role": "assistant",
                "content": self._get_clarification_message(),
                "meta": {
                    "requires_clarification": True,
                    "timestamp": self._get_timestamp()
                }
            }
            
            return {
                "messages": [clarification_msg],
                "search_results": "Clarification needed - country not specified"
            }
            
        except Exception as e:
            logger.error(f"Error in unclear route handling: {str(e)}")
            return {
                "messages": [self._create_error_message(str(e))],
                "search_results": f"Error in unclear route: {str(e)}"
            }

    # === ASSISTANCE NODES ===
    async def _detect_assistance_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> Dict[str, Any]:
        """Wrapper for assistance detection with error handling"""
        try:
            return await self.assistance_node.detect_assistance_intent(state, config)
        except Exception as e:
            logger.error(f"Error in assistance detection: {str(e)}")
            return {"assistance_requested": False}
    
    async def _collect_email_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> Dict[str, Any]:
        """Wrapper for email collection with error handling"""
        try:
            return await self.assistance_node.collect_email_info(state, config)
        except Exception as e:
            logger.error(f"Error in email collection: {str(e)}")
            return {"email_status": "error"}
    
    async def _process_assistance_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> Dict[str, Any]:
        """Wrapper for assistance processing with error handling"""
        try:
            return await self.assistance_node.process_assistance_request(state, config)
        except Exception as e:
            logger.error(f"Error in assistance processing: {str(e)}")
            return {"email_status": "error"}

    # === RESPONSE GENERATION NODE ===
    async def _response_generation_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> dict:
        """Generate final response using retrieved context"""
        start_time = time.time()
        
        try:
            s = state.model_dump()
            
            # Check for existing repair responses and handle properly
            has_repair = self._has_repair_response(s.get("messages", []))
            current_repair_type = state.repair_type
            
            # If we have a repair response, use it directly without LLM call
            if current_repair_type and has_repair:
                logger.info(f"Using existing {current_repair_type} repair response directly")
                return {
                    "messages": [],  # Use existing repair message from state
                    "repair_type": None,  # Clear repair state
                    "original_query": None,
                    "misunderstanding_count": 0
                }
            
            # Check if clarification was already provided
            if self._has_clarification_message(s.get("messages", [])):
                logger.info("Clarification message already provided")
                return {"messages": []}

            # Build system prompt and conversation
            system_prompt = self._build_system_prompt(s)
            conversation_messages = self._build_conversation_messages(system_prompt, s.get("messages", []))
            
            # Filter out repair responses from conversation context to avoid confusion
            filtered_messages = []
            for msg in conversation_messages:
                if hasattr(msg, 'content'):
                    # Skip system message and repair messages for LLM context
                    if not (hasattr(msg, 'type') and msg.type == 'system'):
                        # Check if this is a repair message
                        if isinstance(msg.content, str) and not any(
                            phrase in msg.content.lower() 
                            for phrase in ['excuse', 'malentendu', 'clarifier', 'reformuler']
                        ):
                            filtered_messages.append(msg)
                else:
                    filtered_messages.append(msg)
            
            logger.info("Generating AI response with LLM")
            ai_resp = await self.llm.ainvoke(filtered_messages if filtered_messages else conversation_messages, config)
            
            response_content = ai_resp.content if hasattr(ai_resp, 'content') else str(ai_resp)
            response_time = time.time() - start_time
            logger.info(f"Generated response in {response_time:.2f}s: {response_content[:100]}...")
            
            return {"messages": [message_obj_to_dict(ai_resp)]}
            
        except Exception as e:
            logger.error(f"Error in response generation: {str(e)}")
            return {"messages": [self._create_error_message(str(e))]}

    # === ROUTING FUNCTIONS ===
    def _route_after_repair_check(self, state: MultiCountryLegalState) -> Literal["router", "response_generation"]:
        """Route based on repair detection"""
        logger.debug(f"Repair check - repair_type: {state.repair_type}")
        if state.repair_type:
            logger.debug(f"Routing to response_generation (repair detected: {state.repair_type})")
            return "response_generation"
        else:
            logger.debug("Routing to router (no repair)")
            return "router"
    
    def _route_by_country(self, state: MultiCountryLegalState) -> Literal["benin_retrieval", "madagascar_retrieval", "unclear_route"]:
        """Route after router decision"""
        decision = state.router_decision or "unclear"
        route_map = {
            "benin": "benin_retrieval",
            "madagascar": "madagascar_retrieval",
            "unclear": "unclear_route"
        }
        
        result = route_map.get(decision, "unclear_route")
        logger.debug(f"Country routing: {decision} -> {result}")
        return result
    
    def _route_after_detection(self, state: MultiCountryLegalState) -> Literal["collect_email", "response_generation", "process_assistance"]:
        """Route after assistance detection"""
        if not state.assistance_requested:
            logger.debug("No assistance requested -> response_generation")
            return "response_generation"
        
        has_email = bool(state.user_email and state.user_email.strip())
        has_description = bool(state.assistance_description and state.assistance_description.strip())
        
        logger.debug(f"Assistance routing - email: {has_email}, description: {has_description}")
        
        if not has_email or not has_description:
            logger.debug("Missing email/description -> collect_email")
            return "collect_email"
        else:
            logger.debug("Ready for processing -> process_assistance")
            return "process_assistance"

    # === HELPER METHODS ===
    def _get_last_human_message(self, messages: list) -> Optional[dict]:
        """Get the last human message from conversation"""
        if not messages:
            return None
            
        for msg in reversed(messages):
            if msg.get("role", "").lower() in ("user", "human"):
                return msg
        return None

    def _has_repair_response(self, messages: list) -> bool:
        """Check if there's already a repair response in messages"""
        if not messages:
            return False
        for msg in reversed(messages):
            if (msg.get("role") == "assistant" and 
                msg.get("meta", {}).get("is_repair_response")):
                return True
        return False

    def _has_clarification_message(self, messages: list) -> bool:
        """Check if clarification message exists"""
        if not messages:
            return False
            
        last_msg = messages[-1]
        return (last_msg.get("role") == "assistant" and 
                last_msg.get("meta", {}).get("requires_clarification"))

    def _create_router_response(self, country: str, explanation: str, legal_context: dict) -> dict:
        """Create standardized router response"""
        updated_context = self._update_legal_context(legal_context, country)
        return {
            "router_decision": country,
            "route_explanation": explanation,
            "legal_context": updated_context
        }

    def _update_legal_context(self, legal_context: dict, country: str) -> dict:
        """Update legal context with country information"""
        updated = legal_context.copy() if legal_context else {}
        updated["detected_country"] = country
        
        if country == "benin":
            updated["jurisdiction"] = "Bénin"
        elif country == "madagascar":
            updated["jurisdiction"] = "Madagascar"
        else:
            updated["jurisdiction"] = "Unknown"
            
        return updated

    def _build_system_prompt(self, state: dict) -> str:
        """Build system prompt for AI response"""
        country_name = state.get("legal_context", {}).get("jurisdiction", "Unknown")
        route_explanation = state.get("route_explanation", "")
        search_results = state.get("search_results", "")
        
        # Add repair context if available
        repair_context = ""
        if state.get("repair_type"):
            repair_context = f"\n**CONTEXTE DE RÉPARATION**: L'utilisateur a demandé une {state['repair_type']}."
        
        return f"""
Vous êtes un assistant juridique expert spécialisé dans le droit {country_name}.

**CONTEXTE DE ROUTAGE**: {route_explanation}
{repair_context}

**RÉSULTATS DE RECHERCHE**:
{search_results}

Répondez en vous basant sur les informations juridiques et le contexte conversationnel.
Soyez précis, professionnel et citez les articles de loi pertinents quand c'est possible.
"""

    def _build_conversation_messages(self, system_prompt: str, messages: list) -> list:
        """Build conversation messages for LLM - exclude repair messages to avoid duplication"""
        from langchain_core.messages import SystemMessage
        
        conversation_messages = [SystemMessage(content=system_prompt)]
        
        # Filter messages to avoid repair message confusion
        filtered_messages = []
        for msg in messages:
            # Skip repair messages in LLM context
            if not (msg.get("meta", {}).get("is_repair_response") or 
                    msg.get("meta", {}).get("requires_clarification")):
                filtered_messages.append(msg)
        
        # Limit to recent non-repair messages
        recent_messages = filtered_messages[-6:] if len(filtered_messages) > 6 else filtered_messages
        conversation_messages.extend(dict_to_message_obj(m) for m in recent_messages)
        
        return conversation_messages

    def _get_clarification_message(self) -> str:
        """Get standardized clarification message"""
        return """Je ne peux pas déterminer de quel pays vous parlez. Pourriez-vous préciser si votre question concerne le droit du **Bénin** ou de **Madagascar** ?"""

    def _create_error_message(self, error: str) -> dict:
        """Create standardized error message"""
        return {
            "role": "assistant",
            "content": f"Désolé, une erreur s'est produite lors du traitement de votre demande: {error}",
            "meta": {
                "is_error": True,
                "timestamp": self._get_timestamp()
            }
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp for message metadata"""
        from datetime import datetime
        return datetime.now().isoformat()

    # === DEBUGGING AND MONITORING ===
    def debug_state(self, state: MultiCountryLegalState, step: str) -> None:
        """Debug state information"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"=== STATE DEBUG at {step} ===")
            logger.debug(f"Messages count: {len(state.messages)}")
            logger.debug(f"Repair type: {state.repair_type}")
            logger.debug(f"Router decision: {state.router_decision}")
            logger.debug(f"Assistance requested: {state.assistance_requested}")
            logger.debug(f"Last search query: {state.last_search_query}")
            logger.debug("=== END STATE DEBUG ===")

    def get_conversation_stats(self, state: MultiCountryLegalState) -> dict:
        """Get conversation statistics"""
        messages = state.messages or []
        return {
            "total_messages": len(messages),
            "user_messages": len([m for m in messages if m.get("role") in ["user", "human"]]),
            "assistant_messages": len([m for m in messages if m.get("role") == "assistant"]),
            "repair_messages": len([m for m in messages if m.get("meta", {}).get("is_repair_response")]),
            "last_search_query": state.last_search_query,
            "current_country": state.legal_context.get("detected_country") if state.legal_context else None
        }