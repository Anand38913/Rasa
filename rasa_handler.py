import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class RasaHandler:
    """Handles interactions with Rasa conversation engine"""
    
    def __init__(self):
        self.rasa_url = os.getenv('RASA_URL', 'http://localhost:5005')
        self.webhook_url = f"{self.rasa_url}/webhooks/rest/webhook"
        
        # Greeting messages for different languages
        self.greetings = {
            'hi': 'नमस्ते! मैं आपकी सहायता के लिए यहाँ हूँ। मैं आपकी कैसे मदद कर सकता हूँ?',
            'te': 'నమస్కారం! నేను మీకు సహాయం చేయడానికి ఇక్కడ ఉన్నాను. నేను మీకు ఎలా సహాయం చేయగలను?',
            'en': 'Hello! I am here to assist you. How may I help you today?',
            'ur': 'السلام علیکم! میں آپ کی مدد کے لیے یہاں موجود ہوں۔ میں آپ کی کیسے مدد کر سکتا ہوں؟'
        }
        
        logger.info("RasaHandler initialized")
    
    def get_initial_greeting(self, sender_id, language='hi'):
        """Get initial greeting message"""
        greeting = self.greetings.get(language, self.greetings['en'])
        logger.info(f"Initial greeting for {sender_id} in {language}")
        return greeting
    
    def send_message(self, sender_id, message, language='hi', conversation_history=None):
        """
        Send message to Rasa and get response
        
        Args:
            sender_id: Unique identifier for conversation
            message: User message text
            language: Language code
            conversation_history: Previous conversation context
        
        Returns:
            Bot response text
        """
        try:
            # Prepare metadata
            metadata = {
                'language': language,
                'conversation_history': conversation_history or []
            }
            
            payload = {
                'sender': sender_id,
                'message': message,
                'metadata': metadata
            }
            
            logger.info(f"Sending to Rasa - Sender: {sender_id}, Message: {message}")
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                responses = response.json()
                
                if responses and len(responses) > 0:
                    # Combine all response texts
                    bot_response = ' '.join([r.get('text', '') for r in responses if 'text' in r])
                    logger.info(f"Rasa response: {bot_response}")
                    return bot_response
                else:
                    logger.warning("Empty response from Rasa")
                    return self._get_fallback_response(language)
            else:
                logger.error(f"Rasa error: {response.status_code} - {response.text}")
                return self._get_fallback_response(language)
        
        except requests.exceptions.Timeout:
            logger.error("Rasa request timed out")
            return self._get_fallback_response(language)
        except Exception as e:
            logger.error(f"Error communicating with Rasa: {str(e)}")
            return self._get_fallback_response(language)
    
    def _get_fallback_response(self, language='hi'):
        """Get fallback response when Rasa is unavailable"""
        fallback_messages = {
            'hi': 'क्षमा करें, मैं आपकी बात समझ नहीं पाया। क्या आप कृपया दोहरा सकते हैं?',
            'te': 'క్షమించండి, నేను మీ మాట అర్థం చేసుకోలేకపోయాను. దయచేసి మళ్లీ చెప్పగలరా?',
            'en': 'Sorry, I did not understand that. Could you please repeat?',
            'ur': 'معذرت، میں آپ کی بات سمجھ نہیں پایا۔ کیا آپ براہ کرم دہرا سکتے ہیں؟'
        }
        return fallback_messages.get(language, fallback_messages['en'])
    
    def check_health(self):
        """Check if Rasa server is healthy"""
        try:
            response = requests.get(f"{self.rasa_url}/status", timeout=5)
            return response.status_code == 200
        except:
            return False