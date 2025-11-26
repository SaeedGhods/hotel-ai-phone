# config.py - Hotel AI Configuration

from typing import Dict

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

# Language config: lang code, voice, welcome message with SSML, room prompt (6 languages)
LANGUAGES = {
    1: {
        "lang": "en-US", 
        "voice": "polly.Amy-Neural", 
        "welcome": '<prosody rate="slow">Hello <emphasis level="strong">{caller}</emphasis>, you are using version 0.2.0 of the <say-as interpret-as="characters">A I</say-as> hotel system.</prosody> <prosody rate="medium">Welcome. <break time="0.5s"/> How can I help you today? You can ask for room service, front desk, concierge, or housekeeping.</prosody>',
        "room_prompt": '<prosody rate="medium">To assist better, what\'s your room number? <break time="0.3s"/></prosody>'
    },
    2: {
        "lang": "es-ES", 
        "voice": "polly.Mateo-Neural", 
        "welcome": '<prosody rate="slow">Hola <emphasis level="strong">{caller}</emphasis>, estás usando la versión 0.2.0 del sistema de hotel <say-as interpret-as="characters">A I</say-as>.</prosody> <prosody rate="medium">Bienvenido. <break time="0.5s"/> ¿Cómo puedo ayudarte hoy? Puedes pedir servicio de habitación, recepción, conserjería o limpieza.</prosody>',
        "room_prompt": '<prosody rate="medium">¿Cuál es el número de tu habitación para ayudarte mejor? <break time="0.3s"/></prosody>'
    },
    3: {
        "lang": "fr-FR", 
        "voice": "polly.Bryan-Neural", 
        "welcome": '<prosody rate="slow">Bonjour <emphasis level="strong">{caller}</emphasis>, vous utilisez la version 0.2.0 du système <say-as interpret-as="characters">A I</say-as> de l\'hôtel.</prosody> <prosody rate="medium">Bienvenue. <break time="0.5s"/> Comment puis-je vous aider aujourd\'hui ? Vous pouvez demander le service en chambre, la réception, le concierge ou le ménage.</prosody>',
        "room_prompt": '<prosody rate="medium">Pour mieux vous aider, quel est le numéro de votre chambre ? <break time="0.3s"/></prosody>'
    },
    4: {
        "lang": "de-DE", 
        "voice": "polly.Hans-Neural", 
        "welcome": '<prosody rate="slow">Hallo <emphasis level="strong">{caller}</emphasis>, Sie verwenden Version 0.2.0 des Hotel-A-I-Systems.</prosody> <prosody rate="medium">Willkommen. <break time="0.5s"/> Wie kann ich Ihnen heute helfen? Sie können nach Zimmerservice, Rezeption, Concierge oder Hauswirtschaft fragen.</prosody>',
        "room_prompt": '<prosody rate="medium">Um besser zu helfen, was ist Ihre Zimmernummer? <break time="0.3s"/></prosody>'
    },
    5: {
        "lang": "it-IT", 
        "voice": "polly.Giorgio-Neural", 
        "welcome": '<prosody rate="slow">Ciao <emphasis level="strong">{caller}</emphasis>, stai utilizzando la versione 0.2.0 del sistema hotel A-I.</prosody> <prosody rate="medium">Benvenuto. <break time="0.5s"/> Come posso aiutarti oggi? Puoi chiedere per room service, reception, concierge o housekeeping.</prosody>',
        "room_prompt": '<prosody rate="medium">Per aiutarti meglio, qual è il tuo numero di stanza? <break time="0.3s"/></prosody>'
    },
    6: {
        "lang": "ja-JP", 
        "voice": "polly.Mizuki-Neural", 
        "welcome": '<prosody rate="slow">こんにちは <emphasis level="strong">{caller}</emphasis> 様、ホテルのA-Iシステムバージョン0.2.0をお使いです。</prosody> <prosody rate="medium">ようこそ。<break time="0.5s"/> 今日どのようにお手伝いしましょうか？ルームサービス、フロントデスク、コンシェルジュ、またはハウスキーピングをリクエストできます。</prosody>',
        "room_prompt": '<prosody rate="medium">より良くお手伝いするために、お部屋の番号は何ですか？ <break time="0.3s"/></prosody>'
    }
}
