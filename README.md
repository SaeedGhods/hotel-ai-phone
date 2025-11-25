# Hotel AI Phone System

## Overview
This project turns a hotel phone system into an AI-powered service using a real Twilio phone number. Callers press DTMF buttons (1-4) to select services, speak requests (transcribed via Google STT), get AI responses from xAI's Grok, and hear TTS replies. Deployed on Render for public webhook access.

## Local Setup (Optional for Testing)
1. Install dependencies: `source venv/bin/activate && pip install -r requirements.txt`
2. Set env vars: `export TWILIO_ACCOUNT_SID=your_sid`, `export TWILIO_AUTH_TOKEN=your_token`, `export XAI_API_KEY=your_xai_key`
3. Run: `python app.py` (localhost:5000)
4. Use ngrok: `ngrok http 5000` for temp public URL.

## Render Deployment
1. **Sign up/Login**: Go to [render.com](https://render.com) and create an account (free tier works for starters).
2. **Create New Web Service**:
   - Connect your GitHub repo (push this project to GitHub first if not already).
   - Select the repo.
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py` (matches Procfile)
   - Plan: Free (sleeps after 15 min inactivity; upgrade for always-on).
3. **Environment Variables** (Critical - in Render dashboard under "Environment"):
   - `TWILIO_ACCOUNT_SID`: Your Twilio Account SID (from console.twilio.com)
   - `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token (from console)
   - `XAI_API_KEY`: Your xAI API key (from x.ai)
   - (Optional) `PYTHON_VERSION`: 3.13.0
4. **Deploy**: Hit "Create Web Service". Render builds and deploys (URL like https://hotel-ai-abc.onrender.com).
5. **Auto-Deploys**: Push to GitHub main branch for updates.

## Twilio Configuration
1. **Account Setup**:
   - Sign up at [twilio.com/try-twilio](https://www.twilio.com/try-twilio) (free trial with $15 credit).
   - Verify your phone for outbound calls (not needed for inbound webhooks).
   - In Console (console.twilio.com): Note your Account SID and Auth Token.

2. **Get a Phone Number**:
   - Go to Phone Numbers > Manage > Buy a number (search US/Canada for voice; ~$1/month).
   - Example: +1-555-123-4567 (yours will be real).

3. **Configure Webhook for Voice Calls**:
   - In Twilio Console: Phone Numbers > Manage > Active Numbers > Select your number.
   - Scroll to "Voice & Fax" section.
   - Set "A Call Comes In" to: Webhook
   - Primary Handler: `https://your-render-url.onrender.com/voice` (replace with your Render URL, e.g., https://hotel-ai-abc.onrender.com/voice)
   - HTTP Method: POST
   - Save changes.
   - (Optional) For hangup: Set "When Call Is Hung Up" to webhook `/hangup` if needed.

4. **Test the Integration**:
   - Call your Twilio number from any phone.
   - Press 1-4 for service.
   - Speak your request (e.g., "Order a pizza") – currently placeholder transcription.
   - AI responds via voice.

## Limitations & Next
- Speech-to-Text: Placeholder; integrate Google Cloud STT or Deepgram for real transcription.
- Real-time: For live conversation, use Twilio Media Streams + WebSockets.
- Security: Don't hardcode creds in production; use env vars.

## Services
- 1: Room Service
- 2: Front Desk
- 3: Concierge
- 4: Housekeeping

## Usage
Call the number, select service via button press, then speak to the AI.
