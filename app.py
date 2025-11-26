from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import requests
import os
import json
import re
from typing import Dict

app = Flask(__name__)

# Configure logging for production
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use environment variables for secrets
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')  # Optional, for outbound if needed
client_twilio = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

XAI_API_KEY = os.getenv('XAI_API_KEY')
if not XAI_API_KEY:
    raise ValueError("XAI_API_KEY environment variable not set")

XAI_API_URL = "https://api.x.ai/v1/chat/completions"
XAI_HEADERS = {
    "Authorization": f"Bearer {XAI_API_KEY}",
    "Content-Type": "application/json"
}

# Define hotel services and their descriptions
SERVICES: Dict[int, tuple] = {
    1: ("room service", "Handle food and drink orders for the room. Confirm details, use room number, suggest items."),
    2: ("front desk", "Assist with check-in, check-out, billing, and general inquiries. Check room status/balance."),
    3: ("concierge", "Provide recommendations for local attractions, reservations, and transportation. Personalize based on room/guest."),
    4: ("housekeeping", "Schedule cleaning, request amenities like towels or extra linens. Confirm room and timing."),
    5: ("maintenance", "Handle maintenance requests like AC, plumbing, or room repairs. Schedule and confirm.")
}

# Known caller numbers to names (add more as needed; format +1xxxxxxxxxx)
KNOWN_CALLERS = {
    "+19496693870": "Saeed",  # Your number
    # Add others: "+15551234567": "John",
}

# Simulated hotel data (expand to DB in production)
HOTEL_DATA = {
    "101": {"status": "checked_in", "balance": 50.00, "guest": "Saeed"},
    "102": {"status": "checked_out", "balance": 0.00, "guest": "John"},
    # Add more rooms
}

# Language config: lang code, voice, prompts (auto-detect from speech)
LANGUAGES = {
    1: {"lang": "en-US", "voice": "polly.Amy-Neural"},  # Default
    2: {"lang": "es-ES", "voice": "polly.Mateo-Neural"},
    3: {"lang": "fr-FR", "voice": "polly.Bryan-Neural"},
    4: {"lang": "de-DE", "voice": "polly.Hans-Neural"},
    5: {"lang": "it-IT", "voice": "polly.Giorgio-Neural"},
    6: {"lang": "ja-JP", "voice": "polly.Mizuki-Neural"}
}

# Language detection keywords (simple, based on common words)
LANGUAGE_KEYWORDS = {
    2: ['hola', 'por favor', 'gracias', 'español', 'es'],
    3: ['bonjour', 's\'il vous plaît', 'français', 'fr'],
    4: ['hallo', 'bitte', 'deutsch', 'de'],
    5: ['ciao', 'per favore', 'italiano', 'it'],
    6: ['konnichiwa', 'arigatou', '日本語', 'ja']
}

STATE_FILE = '/tmp/conversations.json'  # Persistent state file
CALL_LOGS_FILE = '/tmp/call_logs.json'  # Log file for dashboard

def load_state():
    """Load conversations from file."""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_state(state):
    """Save conversations to file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def load_call_logs():
    """Load call logs from file."""
    try:
        with open(CALL_LOGS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_call_log(log_entry):
    """Save call log entry."""
    logs = load_call_logs()
    logs.append(log_entry)
    with open(CALL_LOGS_FILE, 'w') as f:
        json.dump(logs, f)

def detect_language(speech_result):
    """Detect language from speech_result keywords."""
    speech_lower = speech_result.lower()
    for lang_id, keywords in LANGUAGE_KEYWORDS.items():
        if any(keyword in speech_lower for keyword in keywords):
            return lang_id
    return 1  # Default English

def get_state(call_sid):
    """Get or create state for call."""
    all_state = load_state()
    if call_sid not in all_state:
        all_state[call_sid] = {'messages': [], 'lang': 1, 'room_number': None, 'caller_name': 'guest'}
    return all_state[call_sid]

def save_state_update(call_sid, state):
    """Update and save state."""
    all_state = load_state()
    all_state[call_sid] = state
    save_state(all_state)

def get_ai_response(messages, room_number=None, service_name=None):
    """Get response from xAI Grok with context."""
    # Limit history to last 10 messages for token efficiency
    if len(messages) > 10:
        messages = messages[-10:]
    
    # Enhanced system prompt for smarter responses
    base_prompt = f"You are a smart, friendly hotel assistant powered by Grok-3. Respond briefly, engagingly, and helpfully. Use context from previous messages."
    if room_number:
        room_data = get_room_data(room_number)
        base_prompt += f" Guest is in room {room_number}. {room_data['guest']}, status: {room_data['status']}, balance: ${room_data['balance']}. Reference if relevant."
    if service_name:
        base_prompt += f" You are assisting with {service_name}."
    if any(keyword in ' '.join([m['content'].lower() for m in messages]) for keyword in ['human', 'manager', 'person', 'complaint', 'issue']):
        base_prompt += " The user wants a human—escalate politely."
    messages.insert(0, {"role": "system", "content": base_prompt})
    
    payload = {
        "model": "grok-3",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 200  # Shorter for voice
    }
    try:
        print(f"xAI Payload: {payload}")  # Debug: Log payload
        response = requests.post(XAI_API_URL, headers=XAI_HEADERS, json=payload, timeout=10)
        print(f"xAI Response Status: {response.status_code}")  # Debug: Log status
        print(f"xAI Response Text: {response.text}")  # Debug: Log full response
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"xAI Request Error: {e}")  # Debug: Log request error
        # Predefined fallback based on service
        fallback = "I'm having trouble connecting to my knowledge base right now. I'll note your request and follow up soon."
        return fallback
    except Exception as e:
        print(f"xAI Unexpected Error: {e}")  # Debug: Log unexpected error
        return "I'm having trouble connecting to my knowledge base right now. I'll note your request and follow up soon."

def get_caller_name(from_number):
    """Get caller name from phone number."""
    normalized = from_number.replace('+1', '')
    return KNOWN_CALLERS.get(from_number, "guest")

def get_room_data(room_number):
    """Get room info from simulated DB."""
    return HOTEL_DATA.get(room_number, {"status": "unknown", "balance": 0.00, "guest": "guest"})

@app.errorhandler(500)
def internal_error(error):
    """Handle internal errors gracefully."""
    resp = VoiceResponse()
    resp.say("Sorry, something went wrong. Please call back or press any key to end.", voice='polly.Amy-Neural')
    resp.hangup()
    return Response(str(resp), mimetype='text/xml')

@app.route('/', methods=['GET'])
def home():
    """Landing page with version info."""
    html = f"""
    <html><body>
    <h1>Hotel AI Phone System</h1>
    <p>Version 0.2.3 - Ready for Twilio calls!</p>
    <p>Call (949) 669-3870 to test: Say language > Room > Service (e.g., "room service hamburger").</p>
    <p>Dashboard: <a href="/dashboard">View call logs</a></p>
    <p>Webhook: POST to /voice for inbound calls.</p>
    </body></html>
    """
    return html

@app.route('/test', methods=['GET'])
def test():
    """Test endpoint for manual verification."""
    return "Hotel AI webhook ready for Twilio calls. Version 0.2.3."

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Simple dashboard to view recent call logs."""
    logs = load_call_logs()
    html = f"""
    <html><body><h1>Hotel AI Call Dashboard (v0.2.3)</h1>
    <p>Recent Calls:</p>
    <ul>
    """
    for log in logs[-10:]:  # Last 10 calls
        html += f"<li><strong>CallSID:</strong> {log['call_sid']} | <strong>Service:</strong> {log['service']} | <strong>Speech:</strong> {log['speech']} | <strong>AI Reply:</strong> {log['ai_reply']}</li>"
    html += "</ul></body></html>"
    return html

@app.route('/voice', methods=['POST'])
def voice():
    call_sid = request.values.get('CallSid', 'default')
    from_number = request.values.get('From', 'unknown')
    caller_name = get_caller_name(from_number)
    
    # Load state
    conv = get_state(call_sid)
    conv['caller_name'] = caller_name
    
    resp = VoiceResponse()
    lang_config = LANGUAGES[1]  # Default English
    welcome_text = f"Hello {caller_name}, you are using version 0.2.3 of the hotel A-I system. I speak most major languages. Welcome. How can I help you today? You can ask for room service, front desk, concierge, housekeeping, or maintenance."
    resp.say(welcome_text, voice=lang_config['voice'], language=lang_config['lang'])
    
    # Ask for room number if not known
    if 'room_number' not in conv or not conv['room_number']:
        resp.say("To assist better, what's your room number?", voice=lang_config['voice'], language=lang_config['lang'])
        gather_room = Gather(input='speech dtmf', num_digits=3, speech_timeout='auto', action='/room_number', method='POST', speech_model='default')
        resp.append(gather_room)
        resp.redirect('/voice')
        return Response(str(resp), mimetype='text/xml')
    
    # Gather DTMF or speech for service selection (voice-first)
    gather = Gather(input='dtmf speech', num_digits=1, speech_timeout='auto', action='/service_selected', method='POST', speech_model='default')
    resp.append(gather)
    
    # Save state
    save_state_update(call_sid, conv)
    save_call_log({
        'call_sid': call_sid,
        'from': from_number,
        'service': 'initial',
        'speech': 'call started',
        'ai_reply': 'welcome'
    })
    
    return Response(str(resp), mimetype='text/xml')

@app.route('/room_number', methods=['POST'])
def room_number():
    call_sid = request.values.get('CallSid', 'default')
    digit = request.values.get('Digits', None)
    speech_result = request.values.get('SpeechResult', '').strip()
    
    conv = get_state(call_sid)
    room_num = None
    if speech_result:
        # Improved extraction with regex for numbers in phrases
        match = re.search(r'\b(\d{3})\b', speech_result)  # Extract 3-digit numbers
        if match:
            room_num = match.group(1)
    elif digit:
        room_num = re.sub(r'\D', '', digit)  # Strip non-digits
    
    if room_num:
        conv['room_number'] = room_num
        room_data = get_room_data(room_num)
        lang_config = LANGUAGES[conv['lang']]
        resp = VoiceResponse()
        resp.say(f"Thanks, noted for room {room_num}. {room_data['guest']}, your balance is ${room_data['balance']}. How can I help?", voice=lang_config['voice'], language=lang_config['lang'])
        gather = Gather(input='dtmf speech', num_digits=1, speech_timeout='auto', action='/service_selected', method='POST', speech_model='default')
        resp.append(gather)
        save_state_update(call_sid, conv)
        return Response(str(resp), mimetype='text/xml')
    
    # Invalid room, reprompt
    lang_config = LANGUAGES[conv['lang']]
    resp = VoiceResponse()
    resp.say("To assist better, what's your room number?", voice=lang_config['voice'], language=lang_config['lang'])
    gather = Gather(input='speech dtmf', num_digits=3, speech_timeout='auto', action='/room_number', method='POST', speech_model='default')
    resp.append(gather)
    save_state_update(call_sid, conv)
    return Response(str(resp), mimetype='text/xml')

@app.route('/service_selected', methods=['POST'])
def service_selected():
    call_sid = request.values.get('CallSid', 'default')
    digit = request.values.get('Digits', None)
    speech_result = request.values.get('SpeechResult', '').lower().strip()
    
    conv = get_state(call_sid)
    lang_config = LANGUAGES[conv['lang']]
    
    print(f"Service Selection Debug: Digit={digit}, Speech={speech_result}, Lang={lang_config['lang']}")  # Debug: Log input
    
    # Auto-detect language from speech_result
    if speech_result:
        detected_lang = detect_language(speech_result)
        if detected_lang != conv['lang']:
            conv['lang'] = detected_lang
            lang_config = LANGUAGES[detected_lang]
            print(f"Detected and switched to lang {detected_lang}")
    
    # Try speech first, then DTMF - expanded keywords for natural phrases
    service_num = None
    if speech_result:
        if any(word in speech_result for word in ['one', 'room', 'service', 'food', 'order', 'meal']):
            service_num = 1
        elif any(word in speech_result for word in ['two', 'front', 'desk', 'check', 'bill', 'inquiry']):
            service_num = 2
        elif any(word in speech_result for word in ['three', 'concierge', 'recommend', 'restaurant']):
            service_num = 3
        elif any(word in speech_result for word in ['four', 'house', 'housekeeping', 'clean', 'towel']):
            service_num = 4
        elif any(word in speech_result for word in ['five', 'maintenance', 'fix', 'ac', 'plumbing']):
            service_num = 5
    elif digit:
        try:
            service_num = int(digit)
        except ValueError:
            pass
    
    if service_num and service_num in SERVICES:
        service_name, desc = SERVICES[service_num]
        conv['service'] = service_name
        conv['system_prompt'] = f"You are a helpful {service_name} assistant in a hotel. {desc}"
        conv['messages'] = [{"role": "system", "content": conv['system_prompt']}]
        
        print(f"Connected to service {service_num}: {service_name}")  # Debug: Log success
        
        resp = VoiceResponse()
        resp.say(f"Connected to {service_name}. How can I help you today? You can speak or press pound to end.", voice=lang_config['voice'], language=lang_config['lang'])
        
        # Gather speech for conversation
        gather = Gather(input='speech', speech_timeout='auto', action='/handle_speech', method='POST', speech_model='default', finish_on_key='#')
        resp.append(gather)
        save_state_update(call_sid, conv)
        return Response(str(resp), mimetype='text/xml')
    
    # Invalid, repeat with clearer prompt
    resp = VoiceResponse()
    resp.say("Sorry, I didn't understand. Tell me what you need: room service, front desk, concierge, housekeeping, or maintenance.", voice=lang_config['voice'], language=lang_config['lang'])
    gather = Gather(input='dtmf speech', num_digits=1, speech_timeout='auto', action='/service_selected', method='POST', speech_model='default')
    resp.append(gather)
    save_state_update(call_sid, conv)
    return Response(str(resp), mimetype='text/xml')

@app.route('/handle_speech', methods=['POST'])
def handle_speech():
    call_sid = request.values.get('CallSid', 'default')
    speech_result = request.values.get('SpeechResult', '').strip()
    
    conv = get_state(call_sid)
    lang_config = LANGUAGES[conv['lang']]
    
    print(f"Speech Input: {speech_result}")  # Debug: Log transcribed speech
    
    if speech_result and conv:
        messages = conv['messages']
        messages.append({"role": "user", "content": speech_result})
        
        # Check for escalation in all messages
        all_content = ' '.join([m['content'].lower() for m in messages])
        if any(keyword in all_content for keyword in ['human', 'manager', 'person', 'complaint', 'issue', 'problem']):
            resp = VoiceResponse()
            resp.say("I'll connect you to a staff member right away. Please hold.", voice=lang_config['voice'], language=lang_config['lang'])
            resp.hangup()
            # Clean up
            all_state = load_state()
            if call_sid in all_state:
                del all_state[call_sid]
            save_state(all_state)
            save_call_log({
                'call_sid': call_sid,
                'service': conv.get('service', 'unknown'),
                'speech': speech_result,
                'ai_reply': 'escalated to human'
            })
            return Response(str(resp), mimetype='text/xml')
        
        ai_reply = get_ai_response(messages, conv.get('room_number'), conv.get('service'))
        messages.append({"role": "assistant", "content": ai_reply})
        
        resp = VoiceResponse()
        resp.say(ai_reply, voice=lang_config['voice'], language=lang_config['lang'])
        resp.pause(length=1)
        if "bye" in speech_result.lower() or "goodbye" in speech_result.lower():
            resp.say("Thank you for calling. Goodbye!", voice=lang_config['voice'], language=lang_config['lang'])
            resp.hangup()
        else:
            resp.say("What else can I help with? Say or press pound to end.", voice=lang_config['voice'], language=lang_config['lang'])
            # Continue conversation with speech
            gather = Gather(input='speech', speech_timeout='auto', action='/handle_speech', method='POST', speech_model='default', finish_on_key='#')
            resp.append(gather)
        save_state_update(call_sid, conv)
        save_call_log({
            'call_sid': call_sid,
            'service': conv.get('service', 'unknown'),
            'speech': speech_result,
            'ai_reply': ai_reply
        })
        return Response(str(resp), mimetype='text/xml')
    
    # No speech or end
    resp = VoiceResponse()
    resp.say("Thank you for calling. Goodbye!", voice=lang_config['voice'], language=lang_config['lang'])
    resp.hangup()
    # Clean up conversation
    all_state = load_state()
    if call_sid in all_state:
        del all_state[call_sid]
    save_state(all_state)
    save_call_log({
        'call_sid': call_sid,
        'service': conv.get('service', 'unknown'),
        'speech': 'end call',
        'ai_reply': 'goodbye'
    })
    return Response(str(resp), mimetype='text/xml')

@app.route('/hangup', methods=['POST'])
def hangup():
    lang_config = LANGUAGES[1]  # Default English for hangup
    resp = VoiceResponse()
    resp.say("Thank you for calling. Goodbye!", voice=lang_config['voice'], language=lang_config['lang'])
    resp.hangup()
    return Response(str(resp), mimetype='text/xml')

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=True)
