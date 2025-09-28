import os
import smtplib
import logging
from email.mime.text import MIMEText  # Correction: MIMEText au lieu de MimeText
from email.mime.multipart import MIMEMultipart  # Correction: MIMEMultipart au lieu de MimeMultipart
from typing import Dict, Optional
import re
import datetime  # Ajout pour la date

from config.settings import settings

logger = logging.getLogger(__name__)

class LegalAssistanceEmailer:
    def __init__(self):
        self.email_address = os.getenv("EMAIL_ADDRESS")
        self.email_password = os.getenv("EMAIL_APP_PASSWORD")
        self.lawyer_email = os.getenv("LAWYER_EMAIL", "lawyer_acfai@gmail.com")
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        
    def is_assistance_request(self, query: str) -> bool:
        """Détecte si l'utilisateur demande une assistance humaine"""
        assistance_keywords = [
            "parler à un avocat", "avocat humain", "assistance humaine",
            "contactez-moi", "rappelez-moi", "assistance téléphonique",
            "besoin d'un avocat", "consultation juridique", "avocat réel",
            "aide humaine", "contact humain", "échange avec un avocat"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in assistance_keywords)
    
    def extract_email_from_text(self, text: str) -> Optional[str]:
        """Extrait un email d'un texte"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, text)
        return matches[0] if matches else None
    
    def validate_email(self, email: str) -> bool:
        """Valide le format d'un email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def send_assistance_request(self, user_email: str, user_query: str, 
                              assistance_description: str, country: str) -> Dict[str, any]:
        """Envoie les emails de confirmation à l'utilisateur et à l'avocat"""
        try:
            # Validation des emails
            if not self.validate_email(user_email):
                return {"success": False, "error": "Format d'email utilisateur invalide"}
            
            if not self.validate_email(self.lawyer_email):
                return {"success": False, "error": "Format d'email avocat invalide"}
            
            # Connexion SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.email_password)
            
            # Email à l'utilisateur
            user_email_sent = self._send_user_confirmation(server, user_email, user_query, country)
            
            # Email à l'avocat
            lawyer_email_sent = self._send_lawyer_notification(server, user_email, user_query, 
                                                             assistance_description, country)
            
            server.quit()
            
            if user_email_sent and lawyer_email_sent:
                logger.info(f"✅ Emails envoyés avec succès pour {user_email}")
                return {
                    "success": True, 
                    "message": "Demande d'assistance envoyée avec succès",
                    "user_email": user_email,
                    "lawyer_email": self.lawyer_email
                }
            else:
                return {"success": False, "error": "Échec de l'envoi des emails"}
                
        except Exception as e:
            logger.error(f"❌ Erreur d'envoi d'email: {e}")
            return {"success": False, "error": f"Erreur SMTP: {str(e)}"}
    
    def _send_user_confirmation(self, server, user_email: str, user_query: str, country: str) -> bool:
        """Envoie l'email de confirmation à l'utilisateur"""
        try:
            message = MIMEMultipart()  # Correction: MIMEMultipart
            message["From"] = self.email_address
            message["To"] = user_email
            message["Subject"] = "📧 Confirmation de votre demande d'assistance juridique"
            
            body = f"""
            <html>
            <body>
                <h2 style="color: #2E86AB;">Confirmation de votre demande d'assistance juridique</h2>
                
                <p>Bonjour,</p>
                
                <p>Nous accusons réception de votre demande d'assistance juridique concernant :</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #2E86AB;">
                    <strong>Question initiale :</strong> {user_query}<br>
                    <strong>Juridiction concernée :</strong> {country}<br>
                    <strong>Votre email :</strong> {user_email}
                </div>
                
                <p>✅ <strong>Notre équipe juridique a été notifiée</strong> et vous contactera dans les plus brefs délais.</p>
                
                <h3>📞 Prochaines étapes :</h3>
                <ul>
                    <li>Un avocat spécialisé vous contactera à l'adresse {user_email}</li>
                    <li>Préparez les documents relatifs à votre situation</li>
                    <li>Durée de réponse estimée : 24-48 heures</li>
                </ul>
                
                <p>Pour toute urgence, vous pouvez répondre directement à cet email.</p>
                
                <hr>
                <p style="color: #6c757d;">
                    <small>
                        ACFAI - Assistance Juridique Intelligente<br>
                        Email : {self.lawyer_email}<br>
                        Ceci est un message automatique, merci de ne pas y répondre directement.
                    </small>
                </p>
            </body>
            </html>
            """
            
            message.attach(MIMEText(body, "html"))  # Correction: MIMEText
            server.send_message(message)
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email utilisateur: {e}")
            return False
    
    def _send_lawyer_notification(self, server, user_email: str, user_query: str, 
                                assistance_description: str, country: str) -> bool:
        """Envoie la notification à l'avocat"""
        try:
            message = MIMEMultipart()  # Correction: MIMEMultipart
            message["From"] = self.email_address
            message["To"] = self.lawyer_email
            message["Subject"] = f"🔔 Nouvelle demande d'assistance juridique - {country}"
            
            body = f"""
            <html>
            <body>
                <h2 style="color: #A23B72;">Nouvelle demande d'assistance juridique</h2>
                
                <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107;">
                    <h3>📋 Informations de la demande :</h3>
                    <p><strong>Utilisateur :</strong> {user_email}</p>
                    <p><strong>Pays/Juridiction :</strong> {country}</p>
                    <p><strong>Question initiale :</strong> {user_query}</p>
                    <p><strong>Description de l'assistance demandée :</strong><br>{assistance_description}</p>
                </div>
                
                <h3>🚀 Action requise :</h3>
                <ul>
                    <li>Contacter l'utilisateur à : {user_email}</li>
                    <li>Spécialité requise : Droit {country}</li>
                    <li>Priorité : Normale</li>
                </ul>
                
                <hr>
                <p style="color: #6c757d;">
                    <small>
                        Système Automatique ACFAI - {settings.CHAT_MODEL}<br>
                        Généré le : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
                    </small>
                </p>
            </body>
            </html>
            """
            
            message.attach(MIMEText(body, "html"))  # Correction: MIMEText
            server.send_message(message)
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email avocat: {e}")
            return False