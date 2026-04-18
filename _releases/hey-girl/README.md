# Hey Girl 🤖

A voice-controlled AI assistant for Windows that can control your PC, answer questions, analyze your screen, and more.

## Features
- 🎤 Wake word activation — just say **"Hey Girl"**
- 🖥 Screenshot + drag-to-select region, then ask the AI about it
- 📎 Upload files (images, PDFs, docs, code) for AI analysis
- 🤖 Dual AI backend — GitHub Models (GPT-4o, free with Copilot) or Anthropic Claude
- 💬 Full conversation memory
- 💰 Cost tracker with daily spending limits
- 🔇 Mute/unmute mic, voice settings, multiple TTS voices

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/eddie7ch/hey-girl.git
cd hey-girl
```

### 2. Create a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your API keys
Copy `.env.example` to `.env` and fill in your keys:
```
ANTHROPIC_API_KEY=your_key_here
GITHUB_TOKEN=your_github_token_here
OPENAI_API_KEY=your_openai_key_here
```

Or use the **⚙ API Keys** button inside the app.

### 5. Run
```bash
python app.py
```
Or double-click **Launch.bat**

## Requirements
- Windows 10/11
- Python 3.11+
- Microphone (for voice features)
