from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import requests
import os
from typing import Dict

app = Flask(__name__)

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
    4: ("housekeeping", "Schedule cleaning, request amenities like towels or extra linens. Confirm room and timing.")
}

# Simulated hotel data (expand to DB in production)
HOTEL_DATA = {
    "101": {"status": "checked_in", "balance": 50.00, "guest": "Saeed"},
    "102": {"status": "checked_out", "balance": 0.00, "guest": "John"},
    # Add more rooms
}

# Known caller numbers to names (add more as needed; format +1xxxxxxxxxx)
KNOWN_CALLERS = {
    "+19496693870": "Saeed",  # Your number
    # Add others: "+15551234567": "John",
}

# Language config: lang code, voice, welcome message, room prompt
LANGUAGES = {
    1: {
        "lang": "en-US", 
        "voice": "polly.Joanna-Neural", 
        "welcome": "You are using version 0.1.6 of the hotel AI system. Welcome to Hotel AI Services. How can I help you today? You can ask for room service, front desk, concierge, or housekeeping.",
        "room_prompt": "To assist better, what's your room number?"
    },
    2: {
        "lang": "es-ES", 
        "voice": "polly.Lucia-Neural", 
        "welcome": "Estás usando la versión 0.1.6 del sistema de IA del hotel. Bienvenido a los servicios de IA del hotel. ¿Cómo puedo ayudarte hoy? Puedes pedir servicio de habitación, recepción, conserjería o limpieza.",
        "room_prompt": "¿Cuál es el número de tu habitación para ayudarte mejor?"
    },
    3: {
        "lang": "fr-FR", 
        "voice": "polly.Lea-Neural", 
        "welcome": "Vous utilisez la version 0.1.6 du système IA de l'hôtel. Bienvenue aux services IA de l'hôtel. Comment puis-je vous aider aujourd'hui ? Vous pouvez demander le service en chambre, la réception, le concierge ou le ménage.",
        "room_prompt": "Pour mieux vous aider, quel est le numéro de votre chambre ?"
    }
}

# Global state for conversation (simple dict; use Redis/sessions in production for multi-user)
current_conversations = {}  # Keyed by CallSid

def get_ai_response(messages, room_number=None, service_name=None):
    """Get response from xAI Grok with context."""
    # Enhanced system prompt for smarter responses
    base_prompt = f"You are a smart, friendly hotel assistant powered by Grok-3. Respond briefly, engagingly, and helpfully. Use context from previous messages."
    if room_number:
        room_data = get_room_data(room_number)
        base_prompt += f" Guest is in room {room_number}. {room_data['guest']}, status: {room_data['status']}, balance: ${room_data['balance']}. Reference if relevant."
    if service_name:
        base_prompt += f" You are assisting with {service_name}."
    if "human" in messages[-1]['content'].lower() or "manager" in messages[-1]['content'].lower():
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
        response = requests.post(XAI_API_URL, headers=XAI_HEADERS, json=payload)
        print(f"xAI Response Status: {response.status_code}")  # Debug: Log status
        print(f"xAI Response Text: {response.text}")  # Debug: Log full response
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"xAI Request Error: {e}")  # Debug: Log request error
        return f"Sorry, I encountered an error: {str(e)}"
    except Exception as e:
        print(f"xAI Unexpected Error: {e}")  # Debug: Log unexpected error
        return f"Sorry, I encountered an error: {str(e)}"

def get_caller_name(from_number):
    """Get caller name from phone number."""
    # Normalize (strip +1 if present)
    normalized = from_number.replace('+1', '')
    return KNOWN_CALLERS.get(from_number, "guest")

def get_room_data(room_number):
    """Get room info from simulated DB."""
    return HOTEL_DATA.get(room_number, {"status": "unknown", "balance": 0.00, "guest": "guest"})

@app.route('/voice', methods=['POST'])
def voice():
    call_sid = request.values.get('CallSid', 'default')
    from_number = request.values.get('From', 'unknown')
    caller_name = get_caller_name(from_number)
    current_conversations[call_sid] = {'messages': [], 'lang': 1, 'room_number': None, 'caller_name': caller_name}  # Added name
    
    resp = VoiceResponse()
    lang_config = LANGUAGES[1]  # Default English
    resp.say(f"Hello {caller_name}, you are using version 0.1.6 of the hotel AI system.", voice=lang_config['voice'], language=lang_config['lang'])
    
    # Language selection prompt (default English if no input)
    resp.say("Please choose your language. Press or say 1 for English, 2 for Spanish, or 3 for French.", voice=lang_config['voice'], language=lang_config['lang'])
    gather_lang = Gather(input='dtmf speech', num_digits=1, speech_timeout='auto', action='/language_selected', method='POST', speech_model='default')
    resp.append(gather_lang)
    resp.redirect('/voice')  # Repeat if no input
    
    return Response(str(resp), mimetype='text/xml')

@app.route('/language_selected', methods=['POST'])
def language_selected():
    call_sid = request.values.get('CallSid', 'default')
    from_number = request.values.get('From', 'unknown')
    caller_name = get_caller_name(from_number)
    digit = request.values.get('Digits', None)
    speech_result = request.values.get('SpeechResult', '').lower().strip()
    
    lang_id = 1  # Default English
    if speech_result:
        if any(word in speech_result for word in ['one', 'english', 'en']):
            lang_id = 1
        elif any(word in speech_result for word in ['two', 'spanish', 'es']):
            lang_id = 2
        elif any(word in speech_result for word in ['three', 'french', 'fr']):
            lang_id = 3
    elif digit:
        try:
            lang_id = int(digit)
            if lang_id not in LANGUAGES:
                lang_id = 1
        except ValueError:
            lang_id = 1
    
    current_conversations[call_sid]['lang'] = lang_id
    lang_config = LANGUAGES[lang_id]
    
    resp = VoiceResponse()
    resp.say(f"Hello {caller_name}, {lang_config['welcome']}", voice=lang_config['voice'], language=lang_config['lang'])
    
    # Ask for room number if not known
    if 'room_number' not in current_conversations[call_sid] or not current_conversations[call_sid]['room_number']:
        resp.say(lang_config['room_prompt'], voice=lang_config['voice'], language=lang_config['lang'])
        gather_room = Gather(input='speech dtmf', num_digits=3, speech_timeout='auto', action='/room_number', method='POST', speech_model='default')
        resp.append(gather_room)
        resp.redirect('/language_selected')
        return Response(str(resp), mimetype='text/xml')
    
    # Gather DTMF or speech for service selection (voice-first, no button mention)
    gather = Gather(input='dtmf speech', num_digits=1, speech_timeout='auto', action='/service_selected', method='POST', speech_model='default')
    resp.append(gather)
    
    # If no input, repeat
    resp.redirect('/language_selected')
    return Response(str(resp), mimetype='text/xml')

@app.route('/room_number', methods=['POST'])
def room_number():
    call_sid = request.values.get('CallSid', 'default')
    digit = request.values.get('Digits', None)
    speech_result = request.values.get('SpeechResult', '').strip()
    
    room_num = None
    if speech_result:
        # Extract number from speech (simple parse, improve with regex for production)
        words = speech_result.lower().split()
        for word in words:
            if word.isdigit() and len(word) == 3:  # Assume 3-digit room
                room_num = word
                break
    elif digit:
        room_num = digit
    
    if room_num:
        current_conversations[call_sid]['room_number'] = room_num
        room_data = get_room_data(room_num)
        lang_config = LANGUAGES[current_conversations[call_sid]['lang']]
        resp = VoiceResponse()
        resp.say(f"Thanks, noted for room {room_num}. {room_data['guest']}, your balance is ${room_data['balance']}. How can I help?", voice=lang_config['voice'], language=lang_config['lang'])
        gather = Gather(input='dtmf speech', num_digits=1, speech_timeout='auto', action='/service_selected', method='POST', speech_model='default')
        resp.append(gather)
        return Response(str(resp), mimetype='text/xml')
    
    # Invalid room, reprompt
    lang_config = LANGUAGES[current_conversations[call_sid]['lang']]
    resp = VoiceResponse()
    resp.say(lang_config['room_prompt'], voice=lang_config['voice'], language=lang_config['lang'])
    gather = Gather(input='speech dtmf', num_digits=3, speech_timeout='auto', action='/room_number', method='POST', speech_model='default')
    resp.append(gather)
    return Response(str(resp), mimetype='text/xml')

@app.route('/service_selected', methods=['POST'])
def service_selected():
    call_sid = request.values.get('CallSid', 'default')
    digit = request.values.get('Digits', None)
    speech_result = request.values.get('SpeechResult', '').lower().strip()
    
    print(f"Service Selection Debug: Digit={digit}, Speech={speech_result}")  # Debug: Log input
    
    # Try speech first, then DTMF - expanded keywords for better matching
    service_num = None
    if speech_result:
        if any(word in speech_result for word in ['one', 'room', 'service', 'food', 'order']):
            service_num = 1
        elif any(word in speech_result for word in ['two', 'front', 'desk', 'check', 'bill', 'billing', 'inquiry']):
            service_num = 2
        elif any(word in speech_result for word in ['three', 'concierge', 'recommend', 'restaurant', 'attraction', 'reservation']):
            service_num = 3
        elif any(word in speech_result for word in ['four', 'house', 'housekeeping', 'clean', 'towel', 'linen', 'amenity']):
            service_num = 4
    elif digit:
        try:
            service_num = int(digit)
        except ValueError:
            pass
    
    if service_num and service_num in SERVICES:
        service_name, desc = SERVICES[service_num]
        conv = current_conversations.get(call_sid, {})
        conv['service'] = service_name
        conv['system_prompt'] = f"You are a helpful {service_name} assistant in a hotel. {desc}"
        conv['messages'] = [{"role": "system", "content": conv['system_prompt']}]
        
        print(f"Connected to service {service_num}: {service_name}")  # Debug: Log success
        
        resp = VoiceResponse()
        resp.say(f"Connected to {service_name}. How can I help you today? You can speak or press pound to end.", voice='alice')
        
        # Gather speech for conversation
        gather = Gather(input='speech', speech_timeout='auto', action='/handle_speech', method='POST', speech_model='default', finish_on_key='#')
        resp.append(gather)
        
        return Response(str(resp), mimetype='text/xml')
    
    # Invalid, repeat with clearer prompt
    resp = VoiceResponse()
    resp.say("Sorry, I didn't understand. Please press or say 1 for Room Service, 2 for Front Desk, 3 for Concierge, or 4 for Housekeeping.", voice='alice')
    resp.pause(0.5)
    gather = Gather(input='dtmf speech', num_digits=1, speech_timeout='auto', action='/service_selected', method='POST', speech_model='default')
    resp.append(gather)
    resp.redirect('/voice')
    return Response(str(resp), mimetype='text/xml')

@app.route('/handle_speech', methods=['POST'])
def handle_speech():
    call_sid = request.values.get('CallSid', 'default')
    speech_result = request.values.get('SpeechResult', '').strip()
    
    print(f"Speech Input: {speech_result}")  # Debug: Log transcribed speech
    
    conv = current_conversations.get(call_sid, {})
    if speech_result and conv:
        messages = conv['messages']
        messages.append({"role": "user", "content": speech_result})
        
        ai_reply = get_ai_response(messages, conv['room_number'], conv['service'])
        messages.append({"role": "assistant", "content": ai_reply})
        
        resp = VoiceResponse()
        resp.say(ai_reply, voice='alice')
        resp.pause(length=1)
        resp.say("What else can I help with? Say or press pound to end.", voice='alice')
        
        # Continue conversation with speech
        gather = Gather(input='speech', speech_timeout='auto', action='/handle_speech', method='POST', speech_model='default', finish_on_key='#')
        resp.append(gather)
        return Response(str(resp), mimetype='text/xml')
    
    # No speech or end
    resp = VoiceResponse()
    resp.say("Thank you for calling. Goodbye!")
    resp.hangup()
    # Clean up conversation
    if call_sid in current_conversations:
        del current_conversations[call_sid]
    return Response(str(resp), mimetype='text/xml')

@app.route('/hangup', methods=['POST'])
def hangup():
    resp = VoiceResponse()
    resp.say("Thank you for calling. Goodbye!")
    resp.hangup()
    return Response(str(resp), mimetype='text/xml')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=True)
