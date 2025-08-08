import speech_recognition as sr 
import webbrowser
import pyttsx3
import requests
import pygame
import os
from gtts import gTTS
import yt_dlp
from openai import OpenAI
import keyboard 
import json
import time
import threading
from vosk import Model , KaldiRecognizer
import pyaudio
from datetime import datetime , time as dtime
import re

# Initialize TTS engine
engine = pyttsx3.init()

# Use your News API key here
newsApi = "NEWS_API_KEYS" # Your News API keys 

#OpenAi Api keys
client = OpenAI(
    api_key="OPENAI_API_KEY",  # Your OpenRouter API key
    base_url="https://openrouter.ai/api/v1"
)

# Wake word 
wake_words = ["jarvis", "jarviss", "service"]
exit_commands = ["thank you", "you can sleep", "sleep", "bye", "exit"]

# reminder file (Create empty file if it doesn't exist)
reminder_file = "reminders.json"
if not os.path.exists(reminder_file):
    with open(reminder_file, "w") as f:
        json.dump([], f)


# Load chat memory 

chat_history = [{"role": "system", "content": "You are JARVIS, a stealthy, smart AI assistant. Be direct and helpful."}]
if os.path.exists("jarvis_chat_history.json"):
    try:
        with open("jarvis_chat_history.json", "r") as f:
            chat_history = json.load(f)
    except:
        pass

# Optional offline speak

def speak_old(text):
    engine.say(text)
    engine.runAndWait()

# gTTS + Pygame TTS
def speak(text , fast=False):
    try:
        if fast: # use fast offline voice for GPT or quick replies
            engine.say(text)
            engine.runAndWait()
        else:
            tts = gTTS(text)
            tts.save('temp.mp3')
            pygame.mixer.init()
            pygame.mixer.music.load('temp.mp3')
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            os.remove("temp.mp3")
    except Exception as e:
        print("TTS error:", e)
        engine.say(text)
        engine.runAndWait()

# Search YouTube for a song and return the video URL
def search_youtube(song_name):
    try:
        ydl_opts = {'quiet': True, 'skip_download': True, 'default_search': 'ytsearch1'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song_name, download=False)
            video_url = info['entries'][0]['webpage_url']
            return video_url
    except Exception as e:
        print("YouTube search error:", e)
        return None
    

# ChatGPT Function

def chat_with_gpt(prompt):
    try:
        # Add the user prompt to the chat history
        chat_history.append({"role": "user", "content": prompt})

        # Call OpenRouter with full conversation history
        response = client.chat.completions.create(
            model="mistralai/codestral-2501",  # Or another valid model
            messages=chat_history,
            max_tokens=512
        )

        # Get reply and add it to chat history
        reply = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": reply})
        with open ("jarvis_chat_history.json","w")as f :
            json.dump(chat_history,f)
        print("GPT Reply:", reply)
        speak(reply , fast=True)

    except Exception as e:
        print("OpenRouter error:", e)
        speak("Sorry, I had trouble thinking just now.")
\
# save reminder 
def save_reminder(task, datetime_str):
    try:
        with open(reminder_file, "r") as f:
            reminders = json.load(f)
        reminders.append({"task": task, "datetime": datetime_str})
        with open(reminder_file, "w") as f:
            json.dump(reminders, f)
        speak(f"Reminder saved: {task} on {datetime_str}")
    except Exception as e:
        print("Reminder save error:", e)
        speak("Failed to save reminder.")


# Background reminder checker
def check_reminders():
    while True:
        try:
            now = datetime.now().strftime("%H:%M")
            with open(reminder_file, "r") as f:
                reminders = json.load(f)

            for reminder in reminders[:]:
                if reminder["time"] == now:
                    speak(f"Reminder: {reminder['task']}")
                    reminders.remove(reminder)

            with open(reminder_file, "w") as f:
                json.dump(reminders, f)

            time.sleep(30)
        except:
            time.sleep(30)

# Process user commands

def processCommand(c):
    c = c.lower()
    print(f"Command received: {c}")

    if "open google" in c:
        speak("Opening Google")
        webbrowser.open("http://google.com")

    elif "open facebook" in c:
        speak("Opening Facebook")
        webbrowser.open("http://facebook.com")

    elif "open youtube" in c:
        speak("Opening YouTube")
        webbrowser.open("http://youtube.com")

    elif "open linkedin" in c:
        speak("Opening Linkedin")
        webbrowser.open("www.linkedin.com")

    elif c.startswith("play"):
        try:
            song_name = c.split(" ", 1)[1]
            speak(f"Searching and playing {song_name} on YouTube")
            video_url = search_youtube(song_name)
            if video_url:
                webbrowser.open(video_url)
            else:
                speak("Sorry, I couldn't find that song.")
        except IndexError:
            speak("Please say the song name after 'play'")

    elif "news" in c:
        try:
            url = f"https://newsapi.org/v2/top-headlines?country=in&category=general,sports,business&apiKey={newsApi}"
            r = requests.get(url)

            if r.status_code == 200:
                data = r.json()
                articles = data.get('articles', [])
            
                if not articles:
                    speak("Sorry, I couldn't find any news at the moment.")
                else:
                    speak("Here are the top headlines from India.")
                    for article in articles[:5]:
                        title = article.get('title')
                        if title:
                            print("Headline:", title)
                            speak(title)
            else:
                speak("Sorry, I couldn't fetch the news right now.")
        except Exception as e:
            print("News fetch error:", e)
            speak("There was an error fetching the news.")

    elif "clear memory" in c:
        chat_history[:] = chat_history[:1]
        if os.path.exists("jarvis_chat_history.json"):
            os.remove("jarvis_chat_history.json")
        speak("Memory cleared , sir.")

    elif "remind me" in c:
        try:
            match = re.search(
                r"remind me to (.*?) on (\d{1,2}(?:st|nd|rd|th)?[\s/-]?[a-zA-Z]+(?:[\s/-]\d{4})?) at (\d{1,2}(:\d{2})?\s?[ap]\.?m\.?)",
                c
            )
            if match:
                task = match.group(1).strip()
                date_str = match.group(2).replace("st", "").replace("nd", "").replace("rd", "").replace("th", "").replace("/", "-").replace(" ", "-")
                time_str = match.group(3).replace(" ", "").replace(".", "").upper()

                # Parse date
                today = datetime.now()
                date_formats = ["%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y", "%d-%B", "%d-%b", "%d-%m"]
                parsed_date = None
                for fmt in date_formats:
                    try:
                        parsed = datetime.strptime(date_str, fmt)
                        if parsed.year == 1900:
                            parsed = parsed.replace(year=today.year)
                        parsed_date = parsed
                        break
                    except:
                        continue

                if not parsed_date:
                    raise ValueError("Invalid date format.")

                # Parse time
                parsed_time = datetime.strptime(time_str, "%I:%M%p").time() if ":" in time_str else datetime.strptime(time_str, "%I%p").time()

                # Combine
                final_datetime = datetime.combine(parsed_date.date(), parsed_time)
                final_str = final_datetime.strftime("%Y-%m-%d %H:%M")
                save_reminder(task, final_str)
            else:
                speak("Please say: remind me to [task] on [date] at [time]")
        except Exception as e:
            print("Reminder date/time error:", e)
            speak("Sorry, I couldn't understand the reminder details.")

    else:
        # NEW: chatGPT fallback trigger
        speak("Let me think...")
        chat_with_gpt(c)

# === Voice Command Listener ===
def listen_for_command():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for command...")
        audio = recognizer.listen(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print("Error listening:", e)
        return ""

# ============ MAIN PROGRAM WITH VOSK WAKE WORD ============

def start_jarvis():
    speak("Hello sir, I’m listening.")
    active = True
    while active:
        try:
            command = listen_for_command()
            print("Heard:", command)

            if any(x in command.lower() for x in exit_commands):
                speak("Okay sir. Going to sleep.")
                active = False
            elif command.strip() == "":
                speak("I didn’t catch that.")
            else:
                processCommand(command)

        except Exception as e_inner:
            print("Listening error:", e_inner)
            speak("An error occurred while listening.")

# ============ WAKE WORD LOOP ============

if __name__ == "__main__":
    speak("Jarvis system is online...")

    threading.Thread(target=check_reminders, daemon=True).start()

    model_path = "vosk-model"
    if not os.path.exists(model_path):
        speak("Vosk model folder not found. Please check installation.")
        exit(1)

    vosk_model = Model(model_path)
    recognizer = KaldiRecognizer(vosk_model, 16000)

    mic = pyaudio.PyAudio()
    stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000,
                      input=True, frames_per_buffer=8192)
    stream.start_stream()

    print("Listening for wake word... (say 'Jarvis')")

    while True:
        data = stream.read(4096, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "")
            print("You said:", text)

            if any(word in text.lower() for word in wake_words):
                print("Wake word detected!")

                start_jarvis()
