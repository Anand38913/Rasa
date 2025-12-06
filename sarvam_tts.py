import os
import logging
import requests
import base64
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class SarvamTTS:
    """Handles text-to-speech conversion using Sarvam AI"""
    
    def __init__(self):
        self.api_key = os.getenv('SARVAM_API_KEY')
        self.api_url = os.getenv('SARVAM_API_URL', 'https://api.sarvam.ai/text-to-speech')
        self.default_voice = os.getenv('DEFAULT_VOICE', 'meera')
        self.voice_speed = float(os.getenv('VOICE_SPEED', 1.0))
        
        if not self.api_key:
            logger.warning("Sarvam API key not configured")
    
    def generate_speech(self, text, language='hi', voice=None):
        """
        Generate speech from text using Sarvam AI
        
        Args:
            text: Text to convert to speech
            language: Language code (hi, te, en, ur)
            voice: Voice model (meera, arjun, or None for default)
        
        Returns:
            Audio URL or None if failed
        """
        if not self.api_key:
            logger.warning("Sarvam API key not configured, skipping TTS")
            return None
        
        try:
            # Select voice based on language and preference
            selected_voice = voice or self._get_voice_for_language(language)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'text': text,
                'language_code': self._get_sarvam_language_code(language),
                'speaker': selected_voice,
                'pitch': 0,
                'pace': self.voice_speed,
                'loudness': 1.5,
                'speech_sample_rate': 8000,  # Optimized for telephony
                'enable_preprocessing': True,
                'model': 'bulbul:v1'
            }
            
            logger.info(f"Generating speech for text: '{text[:50]}...' in {language}")
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Sarvam returns base64 encoded audio
                if 'audio' in result:
                    audio_data = result['audio']
                    
                    # Save audio temporarily and return URL
                    # In production, upload to S3 or CDN
                    audio_url = self._save_audio_temporarily(audio_data, language)
                    logger.info(f"Successfully generated speech audio")
                    return audio_url
                elif 'audio_url' in result:
                    return result['audio_url']
                else:
                    logger.warning("No audio data in Sarvam response")
                    return None
            else:
                logger.error(f"Sarvam API error: {response.status_code} - {response.text}")
                return None
        
        except requests.exceptions.Timeout:
            logger.error("Sarvam API request timed out")
            return None
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return None
    
    def _get_sarvam_language_code(self, language):
        """Map language codes to Sarvam AI language codes"""
        language_map = {
            'hi': 'hi-IN',
            'te': 'te-IN',
            'en': 'en-IN',
            'ur': 'ur-PK'
        }
        return language_map.get(language, 'hi-IN')
    
    def _get_voice_for_language(self, language):
        """Get appropriate voice for language"""
        # Sarvam AI voice mapping
        # meera: Female voice, works well for Hindi, English
        # arjun: Male voice, works well for Hindi, English
        # Add more voices as Sarvam expands
        
        voice_map = {
            'hi': 'meera',  # Female Hindi voice
            'te': 'meera',  # Female Telugu voice
            'en': 'meera',  # Female English voice
            'ur': 'meera'   # Female Urdu voice
        }
        
        return voice_map.get(language, self.default_voice)
    
    def _save_audio_temporarily(self, audio_base64, language):
        """
        Save audio temporarily and return URL
        In production, upload to S3/CDN
        For now, returns a placeholder or saves locally
        """
        try:
            # Create temp directory if it doesn't exist
            temp_dir = 'temp_audio'
            os.makedirs(temp_dir, exist_ok=True)
            
            # Decode base64 audio
            audio_data = base64.b64decode(audio_base64)
            
            # Generate unique filename
            import time
            filename = f"{language}_{int(time.time() * 1000)}.wav"
            filepath = os.path.join(temp_dir, filename)
            
            # Save audio file
            with open(filepath, 'wb') as f:
                f.write(audio_data)
            
            # Return URL (adjust for your deployment)
            server_url = os.getenv('SERVER_URL', 'http://localhost:5000')
            audio_url = f"{server_url}/audio/{filename}"
            
            return audio_url
        
        except Exception as e:
            logger.error(f"Error saving audio: {str(e)}")
            return None
    
    def test_connection(self):
        """Test Sarvam AI API connection"""
        try:
            test_text = "Hello, this is a test."
            result = self.generate_speech(test_text, 'en')
            return result is not None
        except Exception as e:
            logger.error(f"Sarvam connection test failed: {str(e)}")
            return False