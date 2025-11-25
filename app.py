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
    1: ("room service", "Handle food and drink orders for the room."),
    2: ("front desk", "Assist with check-in, check-out, billing, and general inquiries."),
    3: ("concierge", "Provide recommendations for local attractions, reservations, and transportation."),
    4: ("housekeeping", "Schedule cleaning, request amenities like towels or extra linens.")
}

# Global state for conversation (simple dict; use Redis/sessions in production for multi-user)
current_conversations = {}  # Keyed by CallSid

def get_ai_response(messages):
    """Get response from xAI Grok."""
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

@app.route('/voice', methods=['POST'])
def voice():
    call_sid = request.values.get('CallSid', 'default')
    current_conversations[call_sid] = {'messages': []}
    
    resp = VoiceResponse()
    resp.say("Welcome to Hotel AI Services. Press 1 for Room Service, 2 for Front Desk, 3 for Concierge, or 4 for Housekeeping. Or say the number.", voice='alice')
    
    # Gather DTMF or speech for service selection
    gather = Gather(input='dtmf speech', num_digits=1, speech_timeout='auto', action='/service_selected', method='POST', speech_model='default')
    resp.append(gather)
    
    # If no input, repeat
    resp.redirect('/voice')
    return Response(str(resp), mimetype='text/xml')

@app.route('/service_selected', methods=['POST'])
def service_selected():
    call_sid = request.values.get('CallSid', 'default')
    digit = request.values.get('Digits', None)
    speech_result = request.values.get('SpeechResult', '').lower().strip()
    
    # Try speech first, then DTMF
    service_num = None
    if speech_result:
        if 'one' in speech_result or 'room' in speech_result:
            service_num = 1
        elif 'two' in speech_result or 'front' in speech_result:
            service_num = 2
        elif 'three' in speech_result or 'concierge' in speech_result:
            service_num = 3
        elif 'four' in speech_result or 'house' in speech_result:
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
        
        resp = VoiceResponse()
        resp.say(f"Connected to {service_name}. How can I help you today? You can speak or press pound to end.", voice='alice')
        
        # Gather speech for conversation
        gather = Gather(input='speech', speech_timeout='auto', action='/handle_speech', method='POST', speech_model='default', finish_on_key='#')
        resp.append(gather)
        
        return Response(str(resp), mimetype='text/xml')
    
    # Invalid, redirect back
    resp = VoiceResponse()
    resp.say("Sorry, I didn't understand. Please press or say 1 for Room Service, 2 for Front Desk, 3 for Concierge, or 4 for Housekeeping.")
    resp.redirect('/voice')
    return Response(str(resp), mimetype='text/xml')

@app.route('/handle_speech', methods=['POST'])
def handle_speech():
    call_sid = request.values.get('CallSid', 'default')
    speech_result = request.values.get('SpeechResult', '').strip()
    
    conv = current_conversations.get(call_sid, {})
    if speech_result and conv:
        messages = conv['messages']
        messages.append({"role": "user", "content": speech_result})
        
        ai_reply = get_ai_response(messages)
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
