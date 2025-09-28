import re
import logging
from typing import Dict, List, Optional, Literal

logger = logging.getLogger(__name__)

class ConversationRepair:
    def __init__(self):
        self.meta_keywords = {
            "misunderstanding": [
                "pas compris", "mal compris", "vous n'avez pas compris", 
                "ce n'est pas ça", "ce n'est pas ce que je demande",
                "tu n'as pas compris", "vous ne comprenez pas", "faux", "erreur"
            ],
            "rephrase": [
                "reformuler", "autrement", "différemment", "redire", 
                "expliquer autrement", "plus simple", "plus clair",
                "simplifier", "en termes plus simples"
            ],
            "repeat": [
                "répéter", "redire", "encore", "je n'ai pas entendu",
                "peux-tu répéter", "pouvez-vous répéter"
            ],
            "clarification": [
                "précisez", "clarifier", "expliquez", "que voulez-vous dire",
                "je ne comprends pas", "c'est ambigu"
            ]
        }
        
        # Compile regex patterns for each category
        self.patterns = {}
        for category, keywords in self.meta_keywords.items():
            patterns = [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in keywords]
            self.patterns[category] = patterns

    def detect_repair_intent(self, query: str, conversation_history: List[Dict]) -> Optional[str]:
        """Detect if this is a conversation repair request"""
        query_lower = query.lower()
        
        # Check for meta-conversation patterns
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(query_lower):
                    logger.info(f"🔧 Conversation repair detected: {category}")
                    return category
        
        # Additional context-based detection
        if self._is_followup_misunderstanding(query_lower, conversation_history):
            return "misunderstanding"
            
        return None

    def _is_followup_misunderstanding(self, query: str, history: List[Dict]) -> bool:
        """Check if this is a follow-up indicating misunderstanding"""
        if not history or len(history) < 2:
            return False
            
        # Check if last assistant response was a clarification request
        last_assistant_msg = None
        for msg in reversed(history[:-1]):  # Exclude current query
            if msg.get("role") == "assistant":
                last_assistant_msg = msg.get("content", "").lower()
                break
        
        if not last_assistant_msg:
            return False
            
        # If last response was asking for clarification and user is complaining
        clarification_indicators = ["pays", "bénin", "madagascar", "préciser", "quel pays"]
        is_clarification_response = any(indicator in last_assistant_msg for indicator in clarification_indicators)
        is_complaint = any(word in query for word in ["pas", "mal", "faux", "erreur", "compris"])
        
        return is_clarification_response and is_complaint

    def generate_repair_response(self, repair_type: str, conversation_history: List[Dict]) -> str:
        """Generate appropriate response for conversation repair"""
        if repair_type == "misunderstanding":
            return self._handle_misunderstanding(conversation_history)
        elif repair_type == "rephrase":
            return self._handle_rephrase(conversation_history)  # ENHANCED
        elif repair_type == "repeat":
            return self._handle_repeat(conversation_history)
        elif repair_type == "clarification":
            return self._handle_clarification(conversation_history)
        
        return "Je vous écoute, comment puis-je vous aider ?"

    def _handle_rephrase(self, history: List[Dict]) -> str:
        """Enhanced rephrase handling with context awareness"""
        # Find the last assistant response that needs rephrasing
        last_assistant_response = self._find_last_substantive_assistant_response(history)
        
        if not last_assistant_response:
            return "Je vous écoute, quelle est votre question que vous souhaitez reformuler ?"
        
        # Analyze the type of content to rephrase
        response_lower = last_assistant_response.lower()
        
        if any(keyword in response_lower for keyword in ["avocat humain", "assistance", "email", "confirmation"]):
            # It's an assistance-related response
            return self._simplify_assistance_instructions()
        elif any(keyword in response_lower for keyword in ["loi", "code", "article", "droit", "divorce", "mariage"]):
            # It's a legal content response
            return self._ask_legal_specificity(last_assistant_response)
        elif any(keyword in response_lower for keyword in ["pays", "bénin", "madagascar", "juridiction"]):
            # It's a country clarification response
            return "Pourriez-vous préciser si votre question concerne le Bénin ou Madagascar ? C'est important pour que je puisse vous donner la bonne information juridique."
        else:
            # Generic rephrase request
            return "Je vais reformuler. Quel aspect précisément souhaitez-vous que j'explique plus simplement ?"

    def _simplify_assistance_instructions(self) -> str:
        """Provide simplified assistance instructions"""
        return """🔔 **Demande d'assistance simplifiée :**

**Pour parler à un avocat :**
1. **Donnez-moi votre email** 📧
2. **Dites-moi comment vous aider** (ex: "consultation téléphonique", "avis écrit")

**Je transmets tout à notre avocat qui vous contactera directement !**

📧 **Votre email et demande :**"""

    def _ask_legal_specificity(self, original_response: str) -> str:
        """Ask user to specify which legal aspect to rephrase"""
        # Extract key topics from the original response to guide the user
        topics = self._extract_legal_topics(original_response)
        
        if topics:
            topics_str = ", ".join(topics[:3])  # Show max 3 topics
            return f"""🔄 **Je peux reformuler !**

Ma réponse précédente parlait de : **{topics_str}**

**Quel aspect souhaitez-vous que j'explique plus simplement ?**
- Un point particulier ? Lequel ?
- Toute la réponse en général ?
- La procédure à suivre ?

Dites-moi ce qui n'était pas clair !"""
        else:
            return "Je peux reformuler ma réponse précédente. Quel aspect n'était pas clair pour vous ?"

    def _extract_legal_topics(self, text: str) -> List[str]:
        """Extract key legal topics from a response"""
        topics = []
        text_lower = text.lower()
        
        # Common legal topics in your domain
        legal_keywords = {
            "divorce": ["divorce", "séparation", "mariage"],
            "procédure": ["procédure", "tribunal", "juge", "demande"],
            "droits": ["droits", "obligations", "responsabilités"],
            "enfants": ["enfants", "garde", "pension alimentaire"],
            "biens": ["biens", "propriété", "partage", "communauté"]
        }
        
        for topic, keywords in legal_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics

    def _find_last_substantive_assistant_response(self, history: List[Dict]) -> Optional[str]:
        """Find the last meaningful assistant response (skip repair responses)"""
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # Skip very short responses or repair responses
                if (len(content) > 50 and 
                    not msg.get("meta", {}).get("is_repair_response", False) and
                    not any(keyword in content.lower() for keyword in ["répéter", "reformuler", "clarifier"])):
                    return content
        return None

    def _handle_misunderstanding(self, history: List[Dict]) -> str:
        """Handle misunderstanding complaints"""
        original_query = self._find_original_query(history)
        
        if original_query:
            return f"""Je m'excuse si je n'ai pas bien compris votre demande précédente sur "{original_query}".

🔍 **Pour m'aider à mieux vous répondre :**
- Souhaitiez-vous des informations sur le **Bénin** ou **Madagascar** ?
- Voulez-vous que je recherche des textes de loi ou des jurisprudences ?
- Préférez-vous reformuler votre question différemment ?

Je suis là pour vous aider !"""
        else:
            return """Je m'excuse pour ce malentendu. 

🔍 **Pour mieux vous aider :**
- Pourriez préciser si votre question concerne le **droit béninois** ou **malgache** ?
- Souhaitez-vous que je recherche des articles de loi ou des décisions de justice ?

N'hésitez pas à reformuler votre demande !"""

    def _handle_repeat(self, history: List[Dict]) -> str:
        """Handle repeat requests"""
        last_assistant_response = self._find_last_substantive_assistant_response(history)
        
        if last_assistant_response:
            # Truncate very long responses
            if len(last_assistant_response) > 500:
                preview = last_assistant_response[:400] + "... [suite]"
            else:
                preview = last_assistant_response
            
            return f"""🔁 **Voici à nouveau ma réponse précédente :**

{preview}

**Y a-t-il un point particulier que vous souhaitez que je développe ?**"""
        else:
            return "Je vous écoute, quelle est votre question ?"

    def _handle_clarification(self, history: List[Dict]) -> str:
        """Handle clarification requests"""
        return """💡 **Je peux clarifier !**

Pour que je puisse vous expliquer plus clairement :
- **Quel terme ou concept n'était pas clair ?**
- **Quelle partie de ma réponse avez-vous trouvée confuse ?**
- **Souhaitez-vous un exemple concret ?**

N'hésitez pas à être précis !"""

    def _find_original_query(self, history: List[Dict]) -> Optional[str]:
        """Find the original user query that was misunderstood"""
        user_queries = []
        for msg in history:
            if msg.get("role") in ["user", "human"]:
                content = msg.get("content", "")
                # Exclude very short or meta queries
                if len(content) > 10 and not self.detect_repair_intent(content, []):
                    user_queries.append(content)
        
        return user_queries[-2] if len(user_queries) > 1 else user_queries[0] if user_queries else None