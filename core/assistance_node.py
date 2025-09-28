import logging
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig

from models.state_models import MultiCountryLegalState
from core.email_tool import LegalAssistanceEmailer

logger = logging.getLogger(__name__)

class AssistanceNode:
    def __init__(self):
        self.emailer = LegalAssistanceEmailer()
    
    async def detect_assistance_intent(self, state: MultiCountryLegalState, config: RunnableConfig) -> Dict[str, Any]:
        """Détecte si l'utilisateur demande une assistance humaine"""
        s = state.model_dump()
        
        # Trouver le dernier message utilisateur
        last_human = None
        for msg in reversed(s.get("messages", [])):
            if msg.get("role") in ["user", "human"]:
                last_human = msg
                break
        
        if not last_human:
            return {"assistance_requested": False}
        
        user_query = last_human.get("content", "")
        
        # Détection de l'intention d'assistance
        if self.emailer.is_assistance_request(user_query):
            logger.info("🎯 Demande d'assistance humaine détectée")
            
            # Essayer d'extraire l'email du message
            extracted_email = self.emailer.extract_email_from_text(user_query)
            
            return {
                "assistance_requested": True,
                "user_email": extracted_email,  # Peut être None
                "assistance_description": user_query,
                "email_status": "pending"
            }
        
        return {"assistance_requested": False}
    
    async def collect_email_info(self, state: MultiCountryLegalState, config: RunnableConfig) -> Dict[str, Any]:
        """Collecte l'email et la description de l'assistance"""
        s = state.model_dump()
        
        # Vérifier si on a déjà un email
        if s.get("user_email"):
            return {
                "messages": [{
                    "role": "assistant",
                    "content": self._get_email_collection_message(s.get("user_email")),
                    "meta": {"collecting_assistance": True}
                }]
            }
        else:
            return {
                "messages": [{
                    "role": "assistant", 
                    "content": self._get_email_request_message(),
                    "meta": {"collecting_assistance": True}
                }]
            }
    
    async def process_assistance_request(self, state: MultiCountryLegalState, config: RunnableConfig) -> Dict[str, Any]:
        """Traite la demande d'assistance et envoie les emails"""
        s = state.model_dump()
        
        if not s.get("assistance_requested") or not s.get("user_email"):
            return {"email_status": "error", "messages": []}
        
        # Déterminer le pays concerné
        country = s.get("legal_context", {}).get("detected_country", "unknown")
        country_display = "Bénin" if country == "benin" else "Madagascar" if country == "madagascar" else "Non spécifié"
        
        # Envoyer les emails
        user_query = s.get("last_search_query", "Demande d'assistance")
        assistance_desc = s.get("assistance_description", "Assistance juridique demandée")
        
        email_result = self.emailer.send_assistance_request(
            s["user_email"], user_query, assistance_desc, country_display
        )
        
        if email_result["success"]:
            logger.info(f"✅ Demande d'assistance traitée pour {s['user_email']}")
            
            success_message = {
                "role": "assistant",
                "content": self._get_success_message(email_result, s["user_email"]),
                "meta": {"assistance_completed": True}
            }
            
            return {
                "email_status": "sent",
                "messages": [success_message]
            }
        else:
            error_message = {
                "role": "assistant",
                "content": self._get_error_message(email_result.get("error", "Erreur inconnue")),
                "meta": {"assistance_error": True}
            }
            
            return {
                "email_status": "error", 
                "messages": [error_message]
            }
    
    def _get_email_request_message(self) -> str:
        return """🔔 **Demande d'assistance juridique humaine**

Je comprends que vous souhaitez être assisté(e) par un avocat humain. Pour cela, j'ai besoin de :

1. **Votre adresse email** 📧
2. **Une brève description** de la manière dont vous souhaitez être assisté(e)

Par exemple :
- "J'ai besoin d'une consultation téléphonique sur le droit de la famille"
- "Je souhaite un avis écrit sur un contrat"
- "J'ai besoin d'assistance pour une procédure judiciaire"

**Veuillez répondre avec votre email et votre demande :**
"""
    
    def _get_email_collection_message(self, email: str) -> str:
        return f"""📧 **Email détecté : {email}**

Merci ! J'ai bien noté votre email. 

Maintenant, pourriez-vous me décrire **comment vous souhaitez être assisté(e)** par notre avocat ?

Exemples :
- "Consultation téléphonique de 30 minutes"
- "Avis écrit sur ma situation"
- "Accompagnement pour une procédure"
- "Explication détaillée sur un point de droit"

**Votre description :**
"""
    
    def _get_success_message(self, email_result: Dict, user_email: str) -> str:
        return f"""✅ **Demande d'assistance envoyée avec succès !**

📋 **Récapitulatif :**
- **Email utilisateur** : {user_email}
- **Email avocat** : {email_result['lawyer_email']}
- **Statut** : ✅ Emails de confirmation envoyés

📞 **Prochaines étapes :**
1. Vous recevrez un email de confirmation dans quelques minutes
2. Notre avocat vous contactera dans les 24-48 heures
3. Préparez les documents relatifs à votre situation

💼 **En attendant**, puis-je vous aider sur d'autres aspects juridiques ?
"""
    
    def _get_error_message(self, error: str) -> str:
        return f"""❌ **Erreur lors de l'envoi de la demande**

Désolé, une erreur technique s'est produite : {error}

**Veuillez :**
1. Vérifier votre connexion internet
2. Réessayer dans quelques minutes
3. Ou contactez-nous directement à : lawyer_acfai@gmail.com

Je reste disponible pour toute autre question juridique !"""