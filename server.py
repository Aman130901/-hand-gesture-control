import os
import cv2
import time
import json
import threading
import mediapipe as mp
import logging
from flask import Flask, render_template, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from urllib.parse import quote
from werkzeug.utils import secure_filename
from pypdf import PdfReader, PdfWriter

from config import Config
from gesture_engine import GestureEngine
from action_map import ActionMap
from draw_utils import draw_styled_landmarks
from augmentation_utils import augment_image, generate_bulk_augmentations, generate_augmentation_sprite

# --- Configure Logging ---
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# --- Flask Setup ---
app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# Suppression
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# --- Global State ---
class AppState:
    def __init__(self):
        self.lock = threading.Lock()
        
        self.mode = "DETECT" # DETECT, RECORD
        
        # Camera Data
        self.latest_frame_jpg = None
        self.latest_landmarks = None # Raw MP landmarks
        self.camera_active = True
        
        # Gesture Logic
        self.current_gesture = None
        self.last_action_name = ""
        self.last_action_time = 0
        self.cooldown = Config.ACTION_COOLDOWN
        self.last_triggered_gesture = None # Track for single-trigger logic
        
        # Engines
        self.engine = GestureEngine()
        self.action_map = ActionMap()
        self.lanmarker = None
        self.start_time = time.time()
        
        # Stats
        self.fps = 0
        self.stability_score = 0
        self.theme = "DEFAULT"
        self.desktop_window = None # Reference to pywebview window
        
        # Training Metrics (Live Feedback)
        self.training_metrics = {
            "brightness": 0,
            "size": 0,
            "angle": 0,
            "size_range": [1.0, 0.0], # [min, max]
            "angle_range": [1.0, 0.0]  # [min, max]
        }
        
        # Dynamic Camera Settings
        self.camera_config = {
            "width": Config.CAMERA_WIDTH,
            "height": Config.CAMERA_HEIGHT,
            "fps": Config.FPS
        }
        self.camera_needs_update = False

state = AppState()

# --- Background Thread: Camera & Processing ---
camera_thread_started = False

def init_landmarker():
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    
    try:
        base_options = python.BaseOptions(model_asset_path=Config.MODEL_ASSET_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=Config.NUM_HANDS,
            min_hand_detection_confidence=Config.MIN_HAND_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=Config.MIN_HAND_PRESENCE_CONFIDENCE,
            min_tracking_confidence=Config.MIN_TRACKING_CONFIDENCE,
            running_mode=vision.RunningMode.VIDEO)
        return vision.HandLandmarker.create_from_options(options)
    except Exception as e:
        logger.critical(f"Failed to initialize MediaPipe Landmarker: {e}")
        return None

def camera_loop():
    global camera_thread_started
    if camera_thread_started:
        logger.warning("Camera loop already running! Skipping duplicate start.")
        return
    camera_thread_started = True

    logger.info("Starting Camera Loop...")
    
    state.landmarker = init_landmarker()
    if not state.landmarker:
        return

    # Stabilization
    pending_gesture = None
    stability_count = 0
    REQUIRED_STABILITY = Config.GESTURE_STABILITY_FRAMES

    cap = cv2.VideoCapture(Config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, Config.FPS)
    
    if not cap.isOpened():
        logger.critical(f"Could not open camera index {Config.CAMERA_INDEX}")
    
    loop_start = time.time()
    while True:
        if not state.camera_active:
            time.sleep(0.1)
            continue
            
        # Dynamic Reconfiguration
        if state.camera_needs_update:
            logger.info("Reconfiguring camera settings...")
            with state.lock:
                conf = state.camera_config
                state.camera_needs_update = False
            
            cap.release()
            time.sleep(0.5) # Brief pause
            cap = cv2.VideoCapture(Config.CAMERA_INDEX)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, conf['width'])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, conf['height'])
            cap.set(cv2.CAP_PROP_FPS, conf['fps'])
            logger.info(f"Camera reconfigured: {conf}")
            
        success, frame = cap.read()
        if not success:
            logger.warning("Failed to read camera frame. Retrying...")
            time.sleep(1)
            # Try to reconnect
            cap.release()
            cap = cv2.VideoCapture(Config.CAMERA_INDEX)
            continue

        # Flip
        frame = cv2.flip(frame, 1)
        
        # Process
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp = int((time.time() - state.start_time) * 1000)
        
        try:
            result = state.landmarker.detect_for_video(mp_image, timestamp)
        except Exception as e:
            logger.error(f"Inference error: {e}")
            continue
        
        # Update State safely
        with state.lock:
            state.latest_landmarks = None
            
            if result.hand_landmarks:
                state.latest_landmarks = result.hand_landmarks[0]
                
                # Draw
                # Ensure draw_utils is robust or refactored? 
                # Assuming draw_styled_landmarks is safe.
                try:
                    frame = draw_styled_landmarks(frame, result, state.theme)
                except Exception as e:
                    logger.error(f"Drawing error: {e}")
                
                # Logic
                if state.mode == "DETECT":
                    candidate = state.engine.find_gesture(state.latest_landmarks)
                    
                    if candidate == pending_gesture:
                        stability_count += 1
                    else:
                        pending_gesture = candidate
                        stability_count = 0
                    
                    # Only confirm if stable
                    if stability_count >= REQUIRED_STABILITY:
                         confirmed_gesture = pending_gesture
                    else:
                         confirmed_gesture = None

                    state.current_gesture = confirmed_gesture
                    
                    if confirmed_gesture:
                        # Continuous Action Check
                        if state.action_map.is_continuous(confirmed_gesture):
                            try:
                                state.action_map.execute(confirmed_gesture, landmarks=state.latest_landmarks)
                                state.last_action_name = "Tracking" 
                                state.last_action_time = time.time()
                            except Exception as e:
                                logger.error(f"Action execution error: {e}")
                        else:
                            # One-Shot
                            if time.time() - state.last_action_time > state.cooldown:
                                # Check if action is continuous (scrolling, volume, etc)
                                is_cont = state.action_map.is_continuous(confirmed_gesture)
                                
                                # Single Trigger Logic: Only trigger if different from last OR if continuous
                                if confirmed_gesture != state.last_triggered_gesture or is_cont:
                                    logger.info(f"Triggering: {confirmed_gesture} (Cont: {is_cont})")
                                    action = state.action_map.execute(confirmed_gesture, state.latest_landmarks)
                                    if action:
                                        logger.info(f"Action Executed: {action}")
                                        state.last_action_name = action
                                        state.last_action_time = time.time()
                                        
                                        # Pop-up on Action (User Request)
                                        # Only for new One-Shot triggers (excludes continuous tracking/volume)
                                        if confirmed_gesture != state.last_triggered_gesture:
                                             if state.desktop_window:
                                                 try:
                                                     state.desktop_window.restore()
                                                     state.desktop_window.maximize()
                                                     state.desktop_window.focus()
                                                 except: pass
                                        
                                        state.last_triggered_gesture = confirmed_gesture
                                else:
                                    # Still holding the same gesture, do nothing
                                    pass
                    else:
                        # Hand visible, but no gesture confirmed -> Do NOT reset trigger.
                        pass
        


                        
                elif state.mode == "RECORD":
                    # Just ready to save
                    pass
                elif state.mode == "MOUSE":
                    # Virtual Mouse Mode
                    state.action_map._action_smart_mouse(state.latest_landmarks)
                    state.last_action_name = "Virtual Mouse Active"
            else:
                state.current_gesture = None
                state.last_triggered_gesture = None # Reset when hand lost
                pending_gesture = None
                stability_count = 0

            # Clear status text
            if time.time() - state.last_action_time > 3.0:
                 # Don't clear if in Mouse mode to show status
                if state.mode != "MOUSE":
                    state.last_action_name = ""
            
            # --- Training Metrics & Hand Analysis ---
            if state.latest_landmarks:
                # 1. Brightness
                state.training_metrics["brightness"] = int(cv2.mean(frame)[0])
                
                # 2. Hand Size (Approx distance)
                pts = state.latest_landmarks
                x_coords = [p.x for p in pts]
                y_coords = [p.y for p in pts]
                size = (max(x_coords) - min(x_coords)) * (max(y_coords) - min(y_coords))
                state.training_metrics["size"] = size
                
                # Update Session Range (Reset if hand just appeared? No, keep for session)
                if size < state.training_metrics["size_range"][0]: state.training_metrics["size_range"][0] = size
                if size > state.training_metrics["size_range"][1]: state.training_metrics["size_range"][1] = size
                
                # 3. Hand Angle (Rotation)
                # Vector from wrist (0) to middle finger base (9)
                p0 = pts[0]
                p9 = pts[9]
                import math
                angle = math.degrees(math.atan2(p9.y - p0.y, p9.x - p0.x))
                # Normalize to 0-1 range for simplicity in UI? Or just raw.
                state.training_metrics["angle"] = angle
                
                # Update Angle Range (Extreme tracking)
                if angle < state.training_metrics["angle_range"][0]: state.training_metrics["angle_range"][0] = angle
                if angle > state.training_metrics["angle_range"][1]: state.training_metrics["angle_range"][1] = angle
            else:
                # No landmarks, but still check brightness
                state.training_metrics["brightness"] = int(cv2.mean(frame)[0])

            # Stats
            state.stability_score = stability_count

        # Encode for streaming (OUTSIDE LOCK for concurrency)
        try:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                encoded_frame = buffer.tobytes()
                with state.lock:
                    state.latest_frame_jpg = encoded_frame
        except Exception as e:
            logger.error(f"Encoding error: {e}")
        
        # FPS Calculation
        loop_end = time.time()
        dt = loop_end - loop_start
        if dt > 0:
            with state.lock:
                state.fps = int(1.0 / dt)
        loop_start = loop_end
        
        if Config.FPS < 60:
             time.sleep(0.001) # Minimal sleep only if we really need to yield, but for 60FPS+ we want to run hot.


# --- Flask Routes ---
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/float')
def float_view():
    return app.send_static_file('float.html')

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            with state.lock:
                frame = state.latest_frame_jpg
            
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1.0 / Config.FPS)
            
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status', methods=['GET'])
def get_status():
    with state.lock:
        return jsonify({
            "mode": state.mode,
            "detected_gesture": state.current_gesture,
            "last_action": state.last_action_name,
            "is_hand_visible": state.latest_landmarks is not None,
            "fps": state.fps,
            "stability_score": state.stability_score,
            "theme": state.theme,
            "training_metrics": state.training_metrics,
            "camera_config": state.camera_config
        })

@app.route('/api/mode', methods=['POST'])
def set_mode():
    data = request.json
    new_mode = data.get("mode")
    if new_mode in ["DETECT", "RECORD", "MOUSE"]:
        with state.lock:
            state.mode = new_mode
            if new_mode == "RECORD":
                # Reset Exploration Ranges
                state.training_metrics["size_range"] = [1.0, 0.0]
                state.training_metrics["angle_range"] = [180.0, -180.0]
            logger.info(f"Mode switched to {new_mode}")
        return jsonify({"status": "success", "mode": state.mode})
    return jsonify({"error": "Invalid mode"}), 400

@app.route('/api/theme', methods=['POST'])
def set_theme():
    data = request.json
    new_theme = data.get("theme")
    if new_theme:
        with state.lock:
            state.theme = new_theme
        logger.info(f"Theme set to {new_theme}")
    return jsonify({"error": "Invalid theme"}), 400

@app.route('/api/settings', methods=['POST'])
def update_settings():
    data = request.json
    width = data.get("width")
    height = data.get("height")
    fps = data.get("fps")
    
    if width and height and fps:
        with state.lock:
            state.camera_config = {"width": width, "height": height, "fps": fps}
            state.camera_needs_update = True
        return jsonify({"status": "success"})
    return jsonify({"error": "Missing parameters"}), 400

@app.route('/api/gestures', methods=['GET'])
def get_gestures():
    result = []
    # No lock needed for read mostly
    for name, samples in state.engine.gestures.items():
        count = len(samples) if isinstance(samples, list) else 1
        result.append({"name": name, "samples": count})
    return jsonify(result)

@app.route('/api/training/stats')
def training_stats():
    return jsonify(state.engine.get_training_stats())

@app.route('/api/gestures', methods=['GET', 'POST'])
def save_gesture_sample():
    data = request.json
    name = data.get("name")
    
    if not name:
        return jsonify({"error": "Name required"}), 400
        
    with state.lock:
        landmarks = state.latest_landmarks
        frame_jpg = state.latest_frame_jpg
        
    if landmarks:
        if state.engine.save_gesture(name, landmarks):
            # Save Image Sample
            if frame_jpg:
                try:
                    sample_dir = os.path.join("samples", name)
                    os.makedirs(sample_dir, exist_ok=True)
                    timestamp = int(time.time() * 1000)
                    filepath = os.path.join(sample_dir, f"{timestamp}.jpg")
                    with open(filepath, "wb") as f:
                        f.write(frame_jpg)
                    logger.info(f"Saved image sample to {filepath}")
                except Exception as e:
                    logger.error(f"Failed to save image sample: {e}")

            return jsonify({"status": "success", "message": f"Sample added to {name}"})
        else:
            return jsonify({"error": "Failed to save sample"}), 500
    else:
        return jsonify({"error": "No hand detected"}), 404

@app.route('/api/gestures/<name>/images', methods=['GET'])
def get_gesture_images(name):
    try:
        sample_dir = os.path.join("samples", name)
        if not os.path.exists(sample_dir):
            return jsonify([])
        
        files = sorted(os.listdir(sample_dir), reverse=True) # Newest first
        # Filter for jpg
        images = [f for f in files if f.endswith('.jpg')]
        
        # Limit to 30 latest images for performance
        images = images[:30]
        
        # Return URLs (quoted for safety)
        urls = [f"/samples/{quote(name)}/{img}" for img in images]
        return jsonify(urls)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/gestures/<name>/samples/<path:filename>', methods=['DELETE'])
def delete_sample(name, filename):
    try:
        sample_dir = os.path.join("samples", name)
        filepath = os.path.join(sample_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404

        # Logic: Find index of this file in the sorted list to delete from JSON
        # JSON = [Oldest, ..., Newest]
        # Files (Sorted by name/timestamp) = [Oldest, ..., Newest]
        # So index match is direct if we sort files safely.
        
        all_files = sorted([f for f in os.listdir(sample_dir) if f.endswith('.jpg')])
        
        if filename in all_files:
            index = all_files.index(filename)
            
            # Delete from Engine (JSON)
            if state.engine.delete_sample(name, index):
                # Delete File
                os.remove(filepath)
                return jsonify({"status": "success"})
            else:
                 return jsonify({"error": "Failed to update data"}), 500
        else:
             return jsonify({"error": "File sync error"}), 500

    except Exception as e:
        logger.error(f"Sample delete error: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/api/gestures/<name>/samples/<path:filename>/augment', methods=['GET'])
def augment_sample_preview(name, filename):
    try:
        sample_dir = os.path.join("samples", name)
        filepath = os.path.join(sample_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404

        # Read original
        img = cv2.imread(filepath)
        if img is None:
            return jsonify({"error": "Failed to read image"}), 500

        # Augment
        augmented = augment_image(img, fast=True)
        
        # Encode to JPEG
        ret, buffer = cv2.imencode('.jpg', augmented)
        if not ret:
            return jsonify({"error": "Failed to encode image"}), 500
            
        import base64
        encoded = base64.b64encode(buffer).decode('utf-8')
        return jsonify({"augmented_image": f"data:image/jpeg;base64,{encoded}"})

    except Exception as e:
        logger.error(f"Augmentation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/gestures/<name>/samples/<path:filename>/bulk_augment', methods=['GET'])
def bulk_augment_sample_preview(name, filename):
    try:
        sample_dir = os.path.join("samples", name)
        filepath = os.path.join(sample_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404

        # Read original
        img = cv2.imread(filepath)
        if img is None:
            return jsonify({"error": "Failed to read image"}), 500

        # Augment Bulk (100 samples)
        count = request.args.get('count', 100, type=int)
        augmented_list = generate_bulk_augmentations(img, count=count)
        
        results = []
        import base64
        for aug in augmented_list:
            ret, buffer = cv2.imencode('.jpg', aug)
            if ret:
                encoded = base64.b64encode(buffer).decode('utf-8')
                results.append(f"data:image/jpeg;base64,{encoded}")
        
        return jsonify({"augmented_images": results})

    except Exception as e:
        logger.error(f"Bulk augmentation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/gestures/<name>/samples/<path:filename>/augment_raw', methods=['GET'])
def augment_sample_raw(name, filename):
    try:
        sample_dir = os.path.join("samples", name)
        filepath = os.path.join(sample_dir, filename)
        
        if not os.path.exists(filepath):
            return "File not found", 404

        img = cv2.imread(filepath)
        if img is None:
            return "Failed to read image", 500

        # Optional Seed for Determinism
        seed = request.args.get('seed', type=int)
        
        # Optional Resize for Speed
        thumb_w = request.args.get('w', type=int)
        
        augmented = augment_image(img, thumb_w=thumb_w, seed=seed, fast=True)
        
        # Balanced quality (80) - significantly faster for web
        quality = 80
        ret, buffer = cv2.imencode('.jpg', augmented, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ret:
            return "Failed to encode image", 500
            
        return Response(buffer.tobytes(), mimetype='image/jpeg', headers={
            'Cache-Control': 'public, max-age=3600'
        })
    except Exception as e:
        logger.error(f"Raw augmentation error: {e}")
        return str(e), 500

@app.route('/api/gestures/<name>/samples/<path:filename>/sprite', methods=['GET'])
def augment_sample_sprite(name, filename):
    try:
        sample_dir = os.path.join("samples", name)
        filepath = os.path.join(sample_dir, filename)
        
        if not os.path.exists(filepath):
            return "File not found", 404

        img = cv2.imread(filepath)
        if img is None:
            return "Failed to read image", 500

        count = request.args.get('count', 100, type=int)
        # Cap count to 400 to prevent memory issues
        count = min(400, max(1, count))
        
        sprite = generate_augmentation_sprite(img, count=count)
        
        # Web-Optimized quality (85) - Ideal for small tiles
        ret, buffer = cv2.imencode('.jpg', sprite, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ret:
            return "Failed to encode image", 500
            
        return Response(buffer.tobytes(), mimetype='image/jpeg')
    except Exception as e:
        logger.error(f"Sprite augmentation error: {e}")
        return str(e), 500

@app.route('/api/gestures/<name>', methods=['DELETE'])
def delete_gesture(name):
    try:
        if state.engine.delete_gesture(name):
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "Gesture not found"}), 404
    except Exception as e:
        logger.error(f"Gesture delete error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/gestures/<name>/rename', methods=['POST'])
def rename_gesture(name):
    data = request.json
    new_name = data.get("new_name")
    
    if not new_name:
        return jsonify({"error": "New name required"}), 400
        
    if new_name == name:
        return jsonify({"status": "success", "message": "No change"})

    try:
        with state.lock:
            # 1. Rename usage in Engine
            if state.engine.rename_gesture(name, new_name):
                # 2. Rename usage in Action Map
                state.action_map.rename_mapping(name, new_name)
                
                return jsonify({"status": "success"})
            else:
                return jsonify({"error": "Rename failed (Name exists or invalid)"}), 400
    except Exception as e:
        logger.error(f"Gesture rename error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/samples/<path:filename>')
def serve_sample(filename):
    # Cache for 1 year (31536000 seconds) since samples don't change names
    return send_from_directory('samples', filename, max_age=31536000)



@app.route('/api/actions', methods=['GET'])
def get_actions():
    return jsonify(state.action_map.get_available_actions())

@app.route('/api/map', methods=['GET'])
def get_mapping():
    return jsonify(state.action_map.mapping)

@app.route('/api/map', methods=['POST'])
def map_gesture():
    data = request.json
    gesture = data.get("gesture")
    action = data.get("action")
    
    if gesture and action:
        state.action_map.map_gesture(gesture, action)
        logger.info(f"Mapped {gesture} -> {action}")
        return jsonify({"status": "success"})
    return jsonify({"error": "Invalid data"}), 400

@app.route('/api/exec', methods=['POST'])
def exec_action():
    data = request.json
    action = data.get("action")
    if action:
        result = state.action_map.perform_action(action)
        return jsonify({"status": "success", "result": result})
    return jsonify({"error": "No action provided"}), 400

@app.route('/api/split-pdf', methods=['POST'])
def process_split_pdf():
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file uploaded"}), 400
    
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        start_page = int(request.form.get('start_page', 1))
        end_page = int(request.form.get('end_page', 1))
        
        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            temp_path = os.path.join("temp_uploads", filename)
            os.makedirs("temp_uploads", exist_ok=True)
            file.save(temp_path)
            
            reader = PdfReader(temp_path)
            writer = PdfWriter()
            total_pages = len(reader.pages)
            
            if start_page < 1 or end_page > total_pages or start_page > end_page:
                return jsonify({"error": f"Invalid page range (1-{total_pages})"}), 400
            
            for i in range(start_page - 1, end_page):
                writer.add_page(reader.pages[i])
            
            output_filename = f"{os.path.splitext(filename)[0]}_split_{start_page}_to_{end_page}.pdf"
            output_path = os.path.join(os.path.expanduser("~"), "Downloads", output_filename)
            
            # Handle duplicates in downloads
            counter = 1
            base_output = os.path.splitext(output_path)[0]
            while os.path.exists(output_path):
                output_path = f"{base_output}_{counter}.pdf"
                counter += 1
                
            with open(output_path, "wb") as f:
                writer.write(f)
            
            # Clean up temp
            os.remove(temp_path)
            
            return jsonify({
                "status": "success", 
                "message": f"Split complete! Saved to Downloads as {os.path.basename(output_path)}"
            })
            
    except Exception as e:
        logger.error(f"Error splitting PDF: {e}")
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "Unknown error"}), 500

if __name__ == '__main__':
    print("--- SERVER STARTUP ---") # Visible console debug
    logger.info("--- SERVER STARTUP REQUEST ---")
    
    # Move thread startup here to prevent duplicate execution in Flask debug mode/reloader
    logger.info("Starting Background Camera Thread...")
    if not camera_thread_started:
        t = threading.Thread(target=camera_loop, daemon=True)
        t.start()
    
    logger.info("Starting Flask Server...")
    # Using use_reloader=False if needed, but moving the thread usually fixes the double-start
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, use_reloader=False)
