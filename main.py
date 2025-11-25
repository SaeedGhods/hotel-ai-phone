import os
import requests
from typing import Dict

# xAI API configuration
XAI_API_KEY = os.getenv('XAI_API_KEY')
if not XAI_API_KEY:
    raise ValueError("XAI_API_KEY environment variable not set")

XAI_API_URL = "https://api.x.ai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {XAI_API_KEY}",
    "Content-Type": "application/json"
}

# Define hotel services and their descriptions
SERVICES: Dict[str, str] = {
    "room service": "Handle food and drink orders for the room.",
    "front desk": "Assist with check-in, check-out, billing, and general inquiries.",
    "concierge": "Provide recommendations for local attractions, reservations, and transportation.",
    "housekeeping": "Schedule cleaning, request amenities like towels or extra linens."
}

def select_service() -> str:
    """Simulate button press by listing options and getting user input."""
    print("Welcome to Hotel AI Services. Please select a service:")
    for i, service in enumerate(SERVICES.keys(), 1):
        print(f"{i}. {service.replace(' ', '_').title()}")
    
    choice = input("Enter the number of your choice: ")
    try:
        selected = list(SERVICES.keys())[int(choice) - 1]
        print(f"Connecting to {selected}...")
        return selected
    except (ValueError, IndexError):
        print("Invalid choice. Please try again.")
        return select_service()

def ai_conversation(service: str, system_prompt: str) -> None:
    """Handle AI conversation using xAI Grok API via requests."""
    print(f"You are now connected to {service}. How can I help you?")
    
    messages = [{"role": "system", "content": system_prompt}]
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["bye", "goodbye", "exit"]:
            print("Thank you for calling. Goodbye!")
            break
        
        messages.append({"role": "user", "content": user_input})
        
        payload = {
            "model": "grok-beta",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(XAI_API_URL, headers=HEADERS, json=payload)
            response.raise_for_status()
            
            data = response.json()
            ai_reply = data["choices"][0]["message"]["content"]
            print(f"AI ({service}): {ai_reply}")
            
            messages.append({"role": "assistant", "content": ai_reply})
        except requests.exceptions.RequestException as e:
            print(f"Error communicating with AI: {e}")
            break
        except (KeyError, IndexError) as e:
            print(f"Unexpected response format: {e}")
            break

if __name__ == "__main__":
    service = select_service()
    system_prompt = f"You are a helpful {service} assistant in a hotel. {SERVICES[service]}"
    ai_conversation(service, system_prompt)
