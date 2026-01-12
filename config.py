import os

class Config:
    # Camera Settings
    CAMERA_INDEX = 0
    CAMERA_WIDTH = 1280
    CAMERA_HEIGHT = 720
    FPS = 30

    # Model Settings
    MODEL_ASSET_PATH = 'hand_landmarker.task'
    NUM_HANDS = 1
    MIN_HAND_DETECTION_CONFIDENCE = 0.5
    MIN_HAND_PRESENCE_CONFIDENCE = 0.5
    MIN_TRACKING_CONFIDENCE = 0.5

    # Gesture Logic
    GESTURE_STABILITY_FRAMES = 3  # Frames gesture must be held to confirm
    ACTION_COOLDOWN = 0.5  # Seconds between actions
    
    # UI Settings
    DRAW_LANDMARKS = True
    THEME_COLOR = (255, 165, 0) # BGR (Orange)

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    GESTURES_FILE = os.path.join(BASE_DIR, 'gestures.json')
    FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

    # Logging
    LOG_LEVEL = "WARNING"
