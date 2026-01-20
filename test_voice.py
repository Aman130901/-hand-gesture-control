
import speech_recognition as sr
import pyaudio
import time

def test_mic():
    print("--- Testing Microphone ---")
    r = sr.Recognizer()
    print("Available Microphones:")
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print(f"Mic {index}: {name}")

    try:
        # Explicitly use default (index=None) first
        with sr.Microphone() as source:
            print(f"\nUsing Default Mic: {source}")
            print("Adjusting for ambient noise... (Please wait)")
            r.adjust_for_ambient_noise(source, duration=1)
            print("Listening... (Say something)")
            audio = r.listen(source, timeout=5)
            print("Processing...")
            text = r.recognize_google(audio)
            print(f"SUCCESS: Heard '{text}'")
            return True
    except sr.RequestError as e:
        print(f"API ERROR: {e}")
    except sr.UnknownValueError:
        print("ERROR: Audio not understood")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    return False

if __name__ == "__main__":
    if test_mic():
        print("\nVoice System OK.")
    else:
        print("\nVoice System FAILED.")
