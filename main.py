import os
# Suppress TF logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import cv2
import mediapipe as mp
import time
from gesture_engine import GestureEngine
from action_map import ActionMap
from draw_utils import draw_styled_landmarks, draw_ui

# Imports for MediaPipe Tasks
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

def main():
    # Setup MediaPipe HandLandmarker
    base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.VIDEO)
    
    with vision.HandLandmarker.create_from_options(options) as landmarker:
        
        # Initialize Engines
        engine = GestureEngine()
        action_map = ActionMap()

        # Webcam Setup
        cap = cv2.VideoCapture(0)
        
        mode = "DETECT" # or "RECORD"
        last_action_time = 0
        last_action_name = ""
        COOLDOWN = 1.0 # Seconds between actions
        
        recording_name = ""
        typing_mode = False

        print("Started Hand Gesture Control (UI Updated)")
        print("Press 'q' to Quit in the window")
        
        # Stability / Noise Reduction
        pending_gesture = None
        stability_count = 0
        REQUIRED_STABILITY = 3 # Frames to hold before triggering
        stability_progress = 0.0
        
        start_time = time.time()

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Flip for selfie view
            frame = cv2.flip(frame, 1)
            
            # Convert to RGB and MP Image
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Timestamp in ms
            frame_timestamp_ms = int((time.time() - start_time) * 1000)
            
            # Detect
            detection_result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)
            
            # Logic vars
            current_gesture = None
            
            if detection_result.hand_landmarks:
                hand_landmarks = detection_result.hand_landmarks[0]
                
                # Logic per mode
                if mode == "DETECT":
                    candidate_gesture = engine.find_gesture(hand_landmarks)
                    
                    if candidate_gesture:
                        if candidate_gesture == pending_gesture:
                            stability_count += 1
                        else:
                            pending_gesture = candidate_gesture
                            stability_count = 0
                        
                        # Calculate progress for UI (0.0 to 1.0)
                        stability_progress = min(stability_count / REQUIRED_STABILITY, 1.0)
                        
                        if stability_count >= REQUIRED_STABILITY:
                            current_gesture = candidate_gesture
                            
                            # Execute Action with Cooldown
                            if time.time() - last_action_time > COOLDOWN:
                                action_triggered = action_map.execute(current_gesture, landmarks=hand_landmarks)
                                if action_triggered:
                                    last_action_time = time.time()
                                    last_action_name = action_triggered
                    else:
                        pending_gesture = None
                        stability_count = 0
                        stability_progress = 0.0
                
                elif mode == "SELECT_ACTION":
                    # Hand landmarks are not key here, just drawing UI
                    pass
                
                elif mode == "RECORD":
                    # Just ready to save
                    pass
            else:
                 pending_gesture = None
                 stability_count = 0
                 stability_progress = 0.0

            # Clear last action after 3 seconds for UI cleanliness
            if time.time() - last_action_time > 3.0:
                last_action_name = ""

            # Draw Beautiful UI
            # 1. Landmarks
            frame = draw_styled_landmarks(frame, detection_result)
            
            # 2. Overlay
            rec_data = {
                'typing_mode': typing_mode, 
                'name_input': recording_name,
                'last_saved': engine.gestures.get('last_saved_name', "Unknown"),
                'available_actions': action_map.get_available_actions(),
                'stability_progress': stability_progress,
                'pending_gesture': pending_gesture
            }
            # Hack to pass just the name we are currently dealing with if in middle of flow
            if mode == "SELECT_ACTION":
                rec_data['last_saved'] = recording_name # Reuse variable or add new one
            
            frame = draw_ui(frame, mode, current_gesture, last_action_name, rec_data)

            cv2.imshow('Hand Gesture Control', frame)

            # Keyboard Interactivity
            key = cv2.waitKey(1) & 0xFF
            
            if mode == "SELECT_ACTION":
                # Check for number keys 0-9
                if 48 <= key <= 57:
                    idx = key - 48
                    actions = action_map.get_available_actions()
                    if idx < len(actions):
                        chosen_action = actions[idx]
                        # Map it!
                        # We stored the name in 'recording_name' temporarily
                        action_map.map_gesture(recording_name, chosen_action)
                        print(f"Mapped '{recording_name}' to '{chosen_action}'")
                        
                        recording_name = "" # Reset
                        mode = "DETECT"
            
            elif typing_mode:
                if key == 13: # Enter
                    if recording_name and detection_result.hand_landmarks:
                        engine.save_gesture(recording_name, detection_result.hand_landmarks[0])
                        print(f"Saved gesture: {recording_name}")
                        # Transition to SELECT ACTION
                        typing_mode = False
                        mode = "SELECT_ACTION"
                        # Don't clear recording_name yet, we need it for mapping
                    else:
                         recording_name = ""
                         typing_mode = False
                         mode = "DETECT"
                elif key == 8: # Backspace
                    recording_name = recording_name[:-1]
                elif 32 <= key <= 126:
                    recording_name += chr(key)
            else:
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    mode = "RECORD"
                elif key == ord('d'):
                    mode = "DETECT"
                    recording_name = ""
                elif key == ord('s') and mode == "RECORD":
                    typing_mode = True

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
