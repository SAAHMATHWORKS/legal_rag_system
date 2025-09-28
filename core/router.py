import re
import logging
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from models.state_models import RoutingResult
from config.constants import COUNTRY_PATTERNS

logger = logging.getLogger(__name__)

class CountryRouter:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.CHAT_MODEL,
            temperature=settings.CHAT_TEMPERATURE,
            max_tokens=500
        )
        self.country_patterns = {
            "benin": [re.compile(pattern, re.IGNORECASE) for pattern in COUNTRY_PATTERNS["benin"]],
            "madagascar": [re.compile(pattern, re.IGNORECASE) for pattern in COUNTRY_PATTERNS["madagascar"]]
        }

    def detect_country_from_patterns(self, text: str) -> Optional[str]:
        """Détection rapide du pays par motifs"""
        benin_score = sum(1 for pattern in self.country_patterns["benin"] if pattern.search(text))
        madagascar_score = sum(1 for pattern in self.country_patterns["madagascar"] if pattern.search(text))
        
        if benin_score > madagascar_score and benin_score > 0:
            return "benin"
        elif madagascar_score > benin_score and madagascar_score > 0:
            return "madagascar"
        return None

    async def route_query(self, query: str, conversation_history: List[Dict]) -> RoutingResult:
        """Route la requête vers le système juridique approprié"""
        # Détection par motifs
        pattern_result = self.detect_country_from_patterns(query)
        if pattern_result:
            return RoutingResult(
                country=pattern_result,
                confidence="high",
                method="pattern_matching",
                explanation=f"Détecté {pattern_result} à partir de références explicites au pays"
            )
        
        # Contexte de la conversation
        for msg in reversed(conversation_history[-6:]):
            if msg.get("role") in ["user", "assistant"]:
                hist_country = self.detect_country_from_patterns(msg.get("content", ""))
                if hist_country:
                    return RoutingResult(
                        country=hist_country,
                        confidence="medium",
                        method="conversation_context",
                        explanation=f"Inféré {hist_country} à partir du contexte de la conversation"
                    )
        
        # Analyse par LLM
        return await self.llm_route_query(query, conversation_history)

    async def llm_route_query(self, query: str, conversation_history: List[Dict]) -> RoutingResult:
        """Utilise le LLM pour les cas ambigus"""
        context = self._build_conversation_context(conversation_history)
        
        routing_prompt = self._build_routing_prompt(query, context)
        
        try:
            response = await self.llm.ainvoke([SystemMessage(content=routing_prompt)])
            return self._parse_llm_response(response.content)
        except Exception as e:
            logger.warning(f"Échec du routage LLM: {e}")
            return RoutingResult(
                country="unclear",
                confidence="low",
                method="fallback",
                explanation="Impossible de déterminer le pays à partir de la requête"
            )

    def _build_conversation_context(self, conversation_history: List[Dict]) -> str:
        if not conversation_history:
            return "Aucun contexte antérieur"
        
        recent_messages = conversation_history[-4:]
        return "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
                         for msg in recent_messages])

    def _build_routing_prompt(self, query: str, context: str) -> str:
        return f"""
Vous êtes un routeur de pays pour un système d'assistance juridique. Analysez la requête et déterminez quel système juridique est concerné.

**Options disponibles :**
- "benin" - Pour les questions juridiques concernant le Bénin
- "madagascar" - Pour les questions juridiques concernant Madagascar
- "unclear" - Lorsque le pays ne peut pas être déterminé

**Requête actuelle :** "{query}"

**Contexte de la conversation :**
{context}

**Instructions :**
1. Recherchez les mentions explicites de pays
2. Prenez en compte le contexte du système juridique dans l'historique de la conversation
3. Si ce n'est pas clair, répondez par "unclear"

Répondez UNIQUEMENT avec un objet JSON :
{{"country": "benin|madagascar|unclear", "confidence": "high|medium|low", "reasoning": "explication brève"}}
"""

    def _parse_llm_response(self, response_text: str) -> RoutingResult:
        import json
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return RoutingResult(
                country=result.get("country", "unclear"),
                confidence=result.get("confidence", "low"),
                method="llm_analysis",
                explanation=result.get("reasoning", "Analyse LLM")
            )
        raise ValueError("Format de réponse LLM invalide")