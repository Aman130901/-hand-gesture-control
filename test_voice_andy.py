import time
from voice_engine import VoiceEngine

def test_andy():
    print("--- ANDY VOICE TEST ---")
    print("Initializing Voice Engine...")
    ve = VoiceEngine()
    
    # Test TTS immediately
    print("Testing TTS (You should hear 'System Online')...")
    ve.speak("System Online")
    time.sleep(2)
    
    print("\n--- INSTRUCTIONS ---")
    print("1. Say 'Andy'")
    print("   -> Expected: He replies 'Yes sir?'")
    print("2. Say 'Andy Open Notepad'")
    print("   -> Expected: He replies 'Working on it' and opens Notepad")
    print("3. Say 'Hello World'")
    print("   -> Expected: Types 'Hello World'")
    
    print("\nStarting Auto Mode... (Press Ctrl+C to stop)")
    ve.start_auto_mode()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ve.stop_auto_mode()
        print("\nTest Stopped.")

if __name__ == "__main__":
    test_jarvis()
