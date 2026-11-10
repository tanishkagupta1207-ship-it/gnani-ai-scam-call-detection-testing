# 🛡️ Scam-Call Shield

A live scam-call detector that listens, transcribes, and warns you during the call, built for "digital arrest" scams.

Built for the Great Indian AI Internship Challenge by Gnani.ai by Diksha Jain and Tanishka Gupta.

🎥 Demo video: [link]

## The Problem

"Digital arrest" scams are one of the fastest-growing frauds in India. Callers pose as police, CBI or customs officers, accuse the victim of a crime, and keep them on a call for hours while pressuring them to transfer money. Victims, often elderly, are panicked and isolated, and by the time they realise it was a scam, the money is gone.

Most existing defences work after the fact (reporting, blocklists, bank alerts). This scam works because of pressure in the moment, so the warning needs to come in the moment too.

## The Solution

Scam-Call Shield listens to a call live through the browser microphone, transcribes the speech in real time using Gnani.ai's speech-to-text, and analyses the transcript for known digital-arrest patterns. When a call looks like a scam, the user gets a clear warning while the call is still in progress.

## What it detects
1. Fake authority claims (CBI, police, customs, courts)
2. Threats of arrest or legal action
3. Urgency and pressure tactics
4. Instructions to stay on the line or keep the call secret
5. Requests to transfer or "verify" money
   
## How It Works

Browser mic  →  Audio capture  →  Gnani.ai Speech-to-Text  →  Scam pattern analysis  →  Live warning

1. The user starts a session and speaks or plays the call audio near the mic.
2. Audio is captured in the browser and streamed to the backend.
3. Gnani.ai's speech-to-text API returns the transcript.
4. The transcript is checked for scam indicators and a risk level is shown.
5. The user is alerted immediately if the call looks like a digital-arrest scam.
   
## Tech Stack
Speech-to-text: Gnani.ai voice platform
Backend: Python (app.py)
Frontend: Browser-based mic recording
Version control: Git

## Getting Started
### Prerequisites
Python 3.9+
A Gnani.ai API key / access credentials
A browser with microphone access
### Installation
bash
  git clone https://github.com/tanishkagupta1207-ship-it/gnani-ai-scam-call-detection-testing.git
  cd gnani-ai-scam-call-detection-testing
  pip install -r requirements.txt
### Configuration
Add your credentials as environment variables (or in a .env file):

bash
  GNANI_API_KEY=your_key_here
  Run
bash
  python app.py

Then open the local URL shown in the terminal, allow microphone access, and start a session.

### Usage
Open the app in your browser.
Click Start and allow microphone access.
Speak or play a sample call. Live transcription appears on screen.
Watch the risk indicator and warnings update as the conversation develops.

### Limitations

This is a hackathon prototype:

Detection is based on scam patterns and may produce false positives or miss new scripts.
It currently works through the browser microphone, not directly on phone calls.
Language support is limited to what was built and tested.

### Future Scope
Support for more Indian languages, since scammers target people in the language they're most comfortable in
Mobile app or telecom-level integration to protect real phone calls
Alerts to a trusted family member when a high-risk call is detected
Detection of other scam types such as fake KYC, bank, courier and investment calls
A growing pattern library that improves as new scam scripts emerge
### Team
Diksha Jain
Tanishka Gupta

## Acknowledgements

Thanks to Gnani.ai for the voice platform and the opportunity through the Great Indian AI Internship Challenge.
