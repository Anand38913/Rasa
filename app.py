import os
import logging
from flask import Flask, request, Response
from flask_cors import CORS
from dotenv import load_dotenv
from twilio_handler import TwilioHandler
from rasa_handler import RasaHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize handlers
twilio_handler = TwilioHandler()
rasa_handler = RasaHandler()

# Session storage (in production, use Redis or database)
call_sessions = {}


@app.route('/')
def home():
    """Health check endpoint"""
    return {'status': 'healthy', 'service': 'Voice Bot API'}, 200


@app.route('/voice/incoming', methods=['POST'])
def incoming_call():
    """Handle incoming Twilio calls"""
    try:
        call_sid = request.form.get('CallSid')
        from_number = request.form.get('From')
        logger.info(f"Incoming call from {from_number}, CallSid: {call_sid}")
        
        # Get language preference (default to configured default)
        language = request.form.get('language', os.getenv('DEFAULT_LANGUAGE', 'hi'))
        
        # Initialize session
        call_sessions[call_sid] = {
            'from_number': from_number,
            'language': language,
            'conversation_history': []
        }
        
        # Get initial greeting from Rasa
        initial_message = rasa_handler.get_initial_greeting(call_sid, language)
        
        # Generate TwiML response with greeting
        twiml = twilio_handler.generate_greeting_response(initial_message, language)
        
        return Response(str(twiml), mimetype='text/xml')
    
    except Exception as e:
        logger.error(f"Error handling incoming call: {str(e)}")
        error_twiml = twilio_handler.generate_error_response()
        return Response(str(error_twiml), mimetype='text/xml')


@app.route('/voice/process', methods=['POST'])
def process_speech():
    """Process speech input from caller"""
    try:
        call_sid = request.form.get('CallSid')
        speech_result = request.form.get('SpeechResult', '')
        confidence = request.form.get('Confidence', 0.0)
        
        logger.info(f"CallSid: {call_sid}, Speech: {speech_result}, Confidence: {confidence}")
        
        if call_sid not in call_sessions:
            logger.warning(f"Session not found for CallSid: {call_sid}")
            twiml = twilio_handler.generate_error_response()
            return Response(str(twiml), mimetype='text/xml')
        
        session = call_sessions[call_sid]
        language = session['language']
        
        # Send to Rasa for processing
        rasa_response = rasa_handler.send_message(
            call_sid, 
            speech_result, 
            language,
            session['conversation_history']
        )
        
        # Update conversation history
        session['conversation_history'].append({
            'user': speech_result,
            'bot': rasa_response
        })
        
        # Generate TwiML with bot response
        twiml = twilio_handler.generate_response(rasa_response, language)
        
        return Response(str(twiml), mimetype='text/xml')
    
    except Exception as e:
        logger.error(f"Error processing speech: {str(e)}")
        error_twiml = twilio_handler.generate_error_response()
        return Response(str(error_twiml), mimetype='text/xml')


@app.route('/voice/status', methods=['POST'])
def call_status():
    """Handle call status callbacks"""
    call_sid = request.form.get('CallSid')
    call_status = request.form.get('CallStatus')
    
    logger.info(f"Call status update - CallSid: {call_sid}, Status: {call_status}")
    
    # Clean up session when call ends
    if call_status in ['completed', 'failed', 'busy', 'no-answer']:
        if call_sid in call_sessions:
            del call_sessions[call_sid]
            logger.info(f"Session cleaned up for CallSid: {call_sid}")
    
    return {'status': 'received'}, 200


@app.route('/call/initiate', methods=['POST'])
def initiate_call():
    """Endpoint to initiate outbound calls"""
    try:
        data = request.get_json()
        to_number = data.get('to_number')
        language = data.get('language', os.getenv('DEFAULT_LANGUAGE', 'hi'))
        
        if not to_number:
            return {'error': 'to_number is required'}, 400
        
        # Initiate call via Twilio
        call = twilio_handler.initiate_outbound_call(to_number, language)
        
        logger.info(f"Outbound call initiated to {to_number}, CallSid: {call.sid}")
        
        return {
            'status': 'success',
            'call_sid': call.sid,
            'to': to_number,
            'language': language
        }, 200
    
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        return {'error': str(e)}, 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'rasa_status': rasa_handler.check_health(),
        'twilio_status': 'connected'
    }, 200


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    logger.info(f"Starting Flask app on {host}:{port}")
    app.run(host=host, port=port, debug=False)