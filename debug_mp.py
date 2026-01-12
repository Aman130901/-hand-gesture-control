import mediapipe as mp
try:
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python import BaseOptions
    print("Tasks API found!")
except ImportError as e:
    print(f"Tasks API import failed: {e}")
