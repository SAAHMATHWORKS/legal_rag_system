from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.runnables import RunnableConfig
from typing import List, Dict, Any, Optional, Annotated, Literal

from models.state_models import MultiCountryLegalState
from core.router import CountryRouter
from core.retriever import LegalRetriever
from core.assistance_node import AssistanceNode
from utils.helpers import dict_to_message_obj, message_obj_to_dict

class GraphBuilder:
    def __init__(self, router: CountryRouter, benin_retriever: LegalRetriever, 
                 madagascar_retriever: LegalRetriever, llm, checkpointer: AsyncPostgresSaver):
        self.router = router
        self.benin_retriever = benin_retriever
        self.madagascar_retriever = madagascar_retriever
        self.assistance_node = AssistanceNode()
        self.llm = llm
        self.checkpointer = checkpointer

    def build_graph(self) -> StateGraph:
        """Build the complete LangGraph workflow"""
        workflow = StateGraph(MultiCountryLegalState)
        
        # Add nodes
        workflow.add_node("router", self._router_node)
        workflow.add_node("benin_retrieval", self._benin_retrieval_node)
        workflow.add_node("madagascar_retrieval", self._madagascar_retrieval_node)
        workflow.add_node("unclear_route", self._unclear_route_node)
        workflow.add_node("response_generation", self._response_generation_node)
        workflow.add_node("detect_assistance", self._detect_assistance_node)  # Changé ici
        workflow.add_node("collect_email", self._collect_email_node)  # Changé ici
        workflow.add_node("process_assistance", self._process_assistance_node)  # Changé ici
        
        # Add edges
        workflow.add_edge(START, "router")
        workflow.add_conditional_edges("router", self._route_by_country)
        workflow.add_edge("benin_retrieval", "detect_assistance")  # Modifié
        workflow.add_edge("madagascar_retrieval", "detect_assistance")  # Modifié
        workflow.add_edge("unclear_route", "detect_assistance")  # Modifié
        
        # Flux d'assistance
        workflow.add_conditional_edges("detect_assistance", self._route_after_detection)
        workflow.add_edge("collect_email", "process_assistance")
        workflow.add_edge("process_assistance", END)
        
        # Flux normal (pas d'assistance demandée)
        workflow.add_edge("response_generation", END)
        
        return workflow

    # === NODES D'ASSISTANCE (WRAPPERS) ===
    
    async def _detect_assistance_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> Dict[str, Any]:
        """Wrapper pour la détection d'assistance"""
        return await self.assistance_node.detect_assistance_intent(state, config)
    
    async def _collect_email_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> Dict[str, Any]:
        """Wrapper pour la collecte d'email"""
        return await self.assistance_node.collect_email_info(state, config)
    
    async def _process_assistance_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> Dict[str, Any]:
        """Wrapper pour le traitement d'assistance"""
        return await self.assistance_node.process_assistance_request(state, config)

    # === NODES EXISTANTS (inchangés) ===
    
    async def _router_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> dict:
        """Route queries to appropriate country system"""
        s = state.model_dump()
        
        last_human = self._get_last_human_message(s.get("messages", []))
        if not last_human:
            return self._create_router_response("unclear", "No user query found", s["legal_context"])

        user_query = last_human.get("content", "")
        
        try:
            routing_result = await self.router.route_query(user_query, s["messages"])
            updated_context = self._update_legal_context(s["legal_context"], routing_result.country)
            
            return {
                "router_decision": routing_result.country,
                "route_explanation": f"{routing_result.method}: {routing_result.explanation}",
                "legal_context": updated_context
            }
        except Exception as e:
            return self._create_router_response("unclear", f"Router error: {str(e)}", s["legal_context"])

    async def _benin_retrieval_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> dict:
        """Retrieve context from Benin legal database"""
        return await self._country_retrieval_node(state, "benin", self.benin_retriever)

    async def _madagascar_retrieval_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> dict:
        """Retrieve context from Madagascar legal database"""
        return await self._country_retrieval_node(state, "madagascar", self.madagascar_retriever)

    async def _country_retrieval_node(self, state: MultiCountryLegalState, country: str, retriever: LegalRetriever) -> dict:
        """Generic country retrieval implementation"""
        s = state.model_dump()
        last_human = self._get_last_human_message(s.get("messages", []))
        
        if not last_human:
            return {"search_results": f"No query for {country} retrieval"}

        user_query = last_human.get("content", "")
        
        try:
            # MODIFICATION ICI : Récupération du message supplémentaire
            enhanced_docs, detected_articles, applied_filters, supplemental_message = retriever.smart_legal_query(user_query, country)
            search_results = retriever.format_search_results(
                user_query, enhanced_docs, detected_articles, applied_filters, country, supplemental_message
            )
            
            return {
                "search_results": search_results,
                "detected_articles": detected_articles,
                "last_search_query": user_query
            }
        except Exception as e:
            return {
                "search_results": f"Erreur lors de la recherche {country}: {str(e)}",
                "detected_articles": []
            }

    async def _unclear_route_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> dict:
        """Handle unclear routing cases"""
        clarification_msg = {
            "role": "assistant",
            "content": self._get_clarification_message(),
            "meta": {"requires_clarification": True}
        }
        
        return {
            "messages": [clarification_msg],
            "search_results": "Clarification needed - country not specified"
        }

    async def _response_generation_node(self, state: MultiCountryLegalState, config: RunnableConfig) -> dict:
        """Generate final response using retrieved context"""
        s = state.model_dump()
        
        # Check if clarification was already provided
        if self._has_clarification_message(s.get("messages", [])):
            return {"messages": []}

        system_prompt = self._build_system_prompt(s)
        conversation_messages = self._build_conversation_messages(system_prompt, s.get("messages", []))
        
        try:
            ai_resp = await self.llm.ainvoke(conversation_messages, config)
            return {"messages": [message_obj_to_dict(ai_resp)]}
        except Exception as e:
            return {"messages": [self._create_error_message(str(e))]}

    # === FONCTIONS DE ROUTAGE CORRIGÉES ===
    
    def _route_by_country(self, state: MultiCountryLegalState) -> Literal["benin_retrieval", "madagascar_retrieval", "unclear_route"]:
        """Route après le router"""
        decision = state.router_decision or "unclear"
        return {
            "benin": "benin_retrieval",
            "madagascar": "madagascar_retrieval",
            "unclear": "unclear_route"
        }[decision]
    
    def _route_after_detection(self, state: MultiCountryLegalState) -> Literal["collect_email", "response_generation"]:
        """Route après détection d'assistance - CORRIGÉ"""
        if state.assistance_requested:
            if not state.user_email or not state.assistance_description:
                return "collect_email"
            else:
                return "process_assistance"
        else:
            return "response_generation"

    # === HELPER METHODS (inchangés) ===
    
    def _get_last_human_message(self, messages: list) -> dict:
        for msg in reversed(messages):
            if msg.get("role", "").lower() in ("user", "human"):
                return msg
        return None

    def _create_router_response(self, country: str, explanation: str, legal_context: dict) -> dict:
        updated_context = self._update_legal_context(legal_context, country)
        return {
            "router_decision": country,
            "route_explanation": explanation,
            "legal_context": updated_context
        }

    def _update_legal_context(self, legal_context: dict, country: str) -> dict:
        updated = legal_context.copy()
        updated["detected_country"] = country
        if country == "benin":
            updated["jurisdiction"] = "Bénin"
        elif country == "madagascar":
            updated["jurisdiction"] = "Madagascar"
        return updated

    def _has_clarification_message(self, messages: list) -> bool:
        if not messages:
            return False
        last_msg = messages[-1]
        return last_msg.get("role") == "assistant" and last_msg.get("meta", {}).get("requires_clarification")

    def _get_clarification_message(self) -> str:
        return """Je ne peux pas déterminer de quel pays vous parlez. Pourriez-vous préciser si votre question concerne le droit du **Bénin** ou de **Madagascar** ?"""

    def _build_system_prompt(self, state: dict) -> str:
        country_name = state.get("legal_context", {}).get("jurisdiction", "Unknown")
        route_explanation = state.get("route_explanation", "")
        search_results = state.get("search_results", "")
        
        return f"""
Vous êtes un assistant juridique expert spécialisé dans le droit {country_name}.

**CONTEXTE DE ROUTAGE**: {route_explanation}

**RÉSULTATS DE RECHERCHE**:
{search_results}

Répondez en vous basant sur les informations juridiques et le contexte conversationnel.
"""

    def _build_conversation_messages(self, system_prompt: str, messages: list) -> list:
        from langchain_core.messages import SystemMessage
        conversation_messages = [SystemMessage(content=system_prompt)]
        recent_messages = messages[-8:] if len(messages) > 8 else messages
        conversation_messages.extend(dict_to_message_obj(m) for m in recent_messages)
        return conversation_messages

    def _create_error_message(self, error: str) -> dict:
        return {
            "role": "assistant",
            "content": f"Désolé, une erreur s'est produite: {error}",
            "meta": {}
        }