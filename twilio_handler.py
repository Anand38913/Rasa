import os
import logging
from dotenv import load_dotenv

# Import Twilio components (compatible with 8.0.0 - 8.2.x)
try:
    from twilio.rest import Client
    from twilio.twiml.voice_response import VoiceResponse, Gather
except ImportError as e:
    raise ImportError(f"Twilio SDK not installed correctly: {e}")

from sarvam_tts import SarvamTTS

load_dotenv()
logger = logging.getLogger(__name__)


class TwilioHandler:
    """Handles Twilio call operations and TwiML generation"""
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.server_url = os.getenv('SERVER_URL')
        
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            raise ValueError("Twilio credentials not properly configured")
        
        self.client = Client(self.account_sid, self.auth_token)
        self.tts = SarvamTTS()
        logger.info("TwilioHandler initialized successfully")
    
    def initiate_outbound_call(self, to_number, language='hi'):
        """Initiate an outbound call"""
        try:
            webhook_url = f"{self.server_url}/voice/incoming?language={language}"
            status_callback = f"{self.server_url}/voice/status"
            
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=webhook_url,
                status_callback=status_callback,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                timeout=int(os.getenv('CALL_TIMEOUT', 60))
            )
            
            logger.info(f"Outbound call created: {call.sid} to {to_number}")
            return call
        
        except Exception as e:
            logger.error(f"Error initiating outbound call: {str(e)}")
            raise
    
    def generate_greeting_response(self, message, language='hi'):
        """Generate TwiML for initial greeting"""
        response = VoiceResponse()
        
        # Get TTS audio URL
        audio_url = self.tts.generate_speech(message, language)
        
        # Play greeting
        if audio_url:
            response.play(audio_url)
        else:
            # Fallback to Twilio's TTS
            response.say(message, language=self._get_twilio_language(language))
        
        # Gather user input
        gather = Gather(
            input='speech',
            timeout=5,
            action=f'{self.server_url}/voice/process',
            language=self._get_twilio_language(language),
            speech_timeout='auto',
            hints=self._get_speech_hints(language)
        )
        
        response.append(gather)
        
        # If no input, redirect
        response.redirect(f'{self.server_url}/voice/process')
        
        return response
    
    def generate_response(self, message, language='hi', end_call=False):
        """Generate TwiML response with bot message"""
        response = VoiceResponse()
        
        # Get TTS audio URL
        audio_url = self.tts.generate_speech(message, language)
        
        # Play bot response
        if audio_url:
            response.play(audio_url)
        else:
            # Fallback to Twilio's TTS
            response.say(message, language=self._get_twilio_language(language))
        
        if end_call:
            response.hangup()
        else:
            # Gather next user input
            gather = Gather(
                input='speech',
                timeout=5,
                action=f'{self.server_url}/voice/process',
                language=self._get_twilio_language(language),
                speech_timeout='auto',
                hints=self._get_speech_hints(language)
            )
            
            response.append(gather)
            response.redirect(f'{self.server_url}/voice/process')
        
        return response
    
    def generate_error_response(self, language='hi'):
        """Generate error response TwiML"""
        response = VoiceResponse()
        
        error_messages = {
            'hi': 'क्षमा करें, कुछ गलत हो गया। कृपया बाद में पुनः प्रयास करें।',
            'te': 'క్షమించండి, ఏదో తప్పు జరిగింది. దయచేసి తర్వాత మళ్లీ ప్రయత్నించండి.',
            'en': 'Sorry, something went wrong. Please try again later.',
            'ur': 'معذرت، کچھ غلط ہو گیا۔ براہ کرم بعد میں دوبارہ کوشش کریں۔'
        }
        
        error_msg = error_messages.get(language, error_messages['en'])
        
        response.say(error_msg, language=self._get_twilio_language(language))
        response.hangup()
        
        return response
    
    def _get_twilio_language(self, language):
        """Map language codes to Twilio language codes"""
        language_map = {
            'hi': 'hi-IN',
            'te': 'te-IN',
            'en': 'en-IN',
            'ur': 'ur-PK'
        }
        return language_map.get(language, 'en-IN')
    
    def _get_speech_hints(self, language):
        """Get speech hints for better recognition"""
        hints_map = {
            'hi': 'हाँ, नहीं, ठीक है, धन्यवाद',
            'te': 'అవును, కాదు, సరే, ధన్యవాదాలు',
            'en': 'yes, no, okay, thank you',
            'ur': 'ہاں, نہیں, ٹھیک ہے, شکریہ'
        }
        return hints_map.get(language, '')