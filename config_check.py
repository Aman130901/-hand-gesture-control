try:
    import cv2
    print("cv2 imported successfully")
except ImportError as e:
    print(f"Error importing cv2: {e}")

try:
    import mediapipe
    print("mediapipe imported successfully")
except ImportError as e:
    print(f"Error importing mediapipe: {e}")

try:
    import pyautogui
    print("pyautogui imported successfully")
except ImportError as e:
    print(f"Error importing pyautogui: {e}")

try:
    import numpy
    print("numpy imported successfully")
except ImportError as e:
    print(f"Error importing numpy: {e}")
