# 🤖 JARVIS - AI Desktop Assistant (Voice Controlled)

JARVIS is an intelligent, voice-activated desktop assistant built with Python. It responds to wake words like **"Jarvis"**, processes natural language commands, and can perform a variety of tasks including:

- Playing music via YouTube 🎵  
- Reading out the latest news 🗞️  
- Setting reminders with natural language ⏰  
- Chatting using OpenAI (via OpenRouter API) 💬  
- Answering questions & handling unknown prompts with AI ✨

---

## 🔧 Features

- 🎙️ **Voice Recognition** with `Vosk` and `SpeechRecognition`
- 📢 **Text-to-Speech (TTS)** via `gTTS` and `pyttsx3`
- 🔍 **YouTube Music Search** using `yt-dlp`
- 🧠 **GPT Integration** via OpenAI's API (customizable model)
- 📅 **Smart Reminders** with time parsing
- 🌐 **Open websites** (Google, Facebook, YouTube, LinkedIn)
- 📰 **Live News Fetching** (using NewsAPI)
- 🧠 **Chat Memory** for continued conversations

---

## 🧠 Requirements

Install dependencies using:

```bash
pip install -r requirements.txt
```

---

## 🛠️ How to Run

1. Clone this repo:
   ```bash
   git clone https://github.com/yourusername/jarvis-ai-assistant.git
   cd jarvis-ai-assistant
   ```

2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Download and extract a VOSK model (e.g. `vosk-model-small-en-us-0.15`)  
   Place the model in a folder named `vosk-model` inside the project directory.

   [Download models here](https://alphacephei.com/vosk/models)

4. Add your API keys:
   - Replace `OPENAI_API_KEY` with your [OpenRouter](https://openrouter.ai/) API key
   - Replace `NEW_API_KEYS` with your [NewsAPI](https://newsapi.org/) key

5. Run the assistant:
   ```bash
   python jarvis.py
   ```

---

## 📁 Project Structure

```
jarvis/
│
├── jarvis.py                  # Main script
├── requirements.txt           # Python dependencies
├── .gitignore                 # Ignore unnecessary files
├── reminders.json             # Stores reminders
├── jarvis_chat_history.json   # Stores chat memory
├── vosk-model/                # Offline speech recognition model
```

---

## ⚠️ Notes

- Requires an active internet connection for:
  - ChatGPT responses
  - YouTube search
  - News fetching
- Works best with a good microphone
- Reminder time format: `Remind me to [task] on [date] at [time]` (e.g., "remind me to call mom on 8 August at 5 pm")

---

## 🚀 Credits

- [OpenRouter](https://openrouter.ai) - for GPT API access  
- [Vosk](https://alphacephei.com/vosk/) - for offline speech recognition  
- [gTTS](https://pypi.org/project/gTTS/) - for Google Text-to-Speech  
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - for YouTube integration  
- [NewsAPI](https://newsapi.org/) - for fetching current headlines

---

## 📜 License

MIT License – feel free to use, share, and modify.

---

## 💡 Future Ideas

- Add email & calendar integration  
- Build a GUI using Tkinter or PyQt  
- Add voice-controlled file management  
- Expand reminder system to daily/weekly tasks