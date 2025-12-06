"""
Outbound Call Initiator Script
Usage: python outbound_caller.py <phone_number> <language>
Example: python outbound_caller.py +919876543210 hi
"""

import os
import sys
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initiate_call(to_number, language='hi'):
    """
    Initiate an outbound call
    
    Args:
        to_number: Phone number to call (E.164 format)
        language: Language code (hi, te, en, ur)
    """
    server_url = os.getenv('SERVER_URL', 'http://localhost:5000')
    endpoint = f"{server_url}/call/initiate"
    
    payload = {
        'to_number': to_number,
        'language': language
    }
    
    try:
        logger.info(f"Initiating call to {to_number} in {language}")
        
        response = requests.post(endpoint, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Call initiated successfully!")
            logger.info(f"Call SID: {result.get('call_sid')}")
            logger.info(f"To: {result.get('to')}")
            logger.info(f"Language: {result.get('language')}")
            return result
        else:
            logger.error(f"Failed to initiate call: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
    
    except requests.exceptions.ConnectionError:
        logger.error(f"Could not connect to server at {server_url}")
        logger.error("Make sure the Flask app is running")
        return None
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        return None


def validate_phone_number(phone_number):
    """Validate phone number format"""
    if not phone_number.startswith('+'):
        logger.warning("Phone number should be in E.164 format (e.g., +919876543210)")
        return False
    
    if len(phone_number) < 10:
        logger.warning("Phone number seems too short")
        return False
    
    return True


def validate_language(language):
    """Validate language code"""
    supported_languages = os.getenv('SUPPORTED_LANGUAGES', 'hi,te,en,ur').split(',')
    
    if language not in supported_languages:
        logger.warning(f"Language '{language}' not supported")
        logger.info(f"Supported languages: {', '.join(supported_languages)}")
        return False
    
    return True


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python outbound_caller.py <phone_number> [language]")
        print("Example: python outbound_caller.py +919876543210 hi")
        print("\nSupported languages:")
        print("  hi - Hindi")
        print("  te - Telugu")
        print("  en - English")
        print("  ur - Urdu")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else 'hi'
    
    # Validate inputs
    if not validate_phone_number(phone_number):
        sys.exit(1)
    
    if not validate_language(language):
        sys.exit(1)
    
    # Initiate the call
    result = initiate_call(phone_number, language)
    
    if result:
        print("\n✓ Call initiated successfully!")
        print(f"Monitor the call status in your Twilio console or check logs")
    else:
        print("\n✗ Failed to initiate call")
        sys.exit(1)


if __name__ == '__main__':
    main()