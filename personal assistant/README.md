# 🤖 Personal Assistant Chatbot

A simple, standalone Gemini API-operated personal assistant chatbot.

## Features
- **ChatGPT-style Web UI**: Clean modern dark theme with avatars, typing indicators, suggested questions, and quick settings.
- **Zero extra packages needed**: Built purely with Python standard library (`http.server`, `urllib`).
- **Terminal CLI mode**: Also runs directly in your console if you prefer.
- **Powered by Google Gemini**: Uses the fast `gemini-2.5-flash` model.

---

## How to Run

### 1. Web UI Mode (Recommended)
From the project folder or inside `personal assistant`:
```powershell
python "personal assistant/app.py"
```
Or:
```powershell
cd "personal assistant"
python app.py
```

Then open your browser at:
👉 **http://localhost:8080**

Enter your Gemini API key in the sidebar settings, and start chatting!

---

### 2. Terminal CLI Mode
To chat right inside your terminal:
```powershell
python "personal assistant/app.py" --cli
```

