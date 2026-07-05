# 🖐️ Hand Gesture Control — Multi-Domain Gesture Automation System

**Hand Gesture Control** turns a regular webcam into a full desktop control interface. Using MediaPipe hand-tracking, it recognizes custom hand gestures in real time and maps them to keyboard shortcuts, mouse actions, voice commands, and domain-specific workflows — from a virtual mouse and presentation remote to a gesture-based classroom attendance system.

It runs as a local Flask server rendered inside a native desktop window (via `pywebview`), with a browser-based control panel for training gestures, configuring actions, and switching between different operating "domains."

---

## ✨ Features

- **Real-time hand tracking** using MediaPipe's Hand Landmarker, tuned for low-resource CPUs and older webcams
- **Custom gesture training** — record your own gestures (fist, peace sign, open palm, etc.) directly from the UI, with live feedback on brightness, hand size, and angle during capture
- **Data augmentation pipeline** for training samples, improving gesture recognition robustness across lighting and angle variation
- **Fully configurable action mapping** — map any gesture to keyboard shortcuts, media controls, screenshots, window switching, or app-specific actions, including **per-application profiles**
- **Virtual mouse mode** — move the cursor and perform left/right click and drag using pinch gestures
- **Voice command engine** — hands-free command recognition layered on top of gesture control
- **Domain-specific modes** — the app adapts its UI and available actions to different real-world contexts:
  - **Hub** — general desktop control
  - **Office/Presentation** — slide navigation and presentation remote
  - **Medical** — hands-free control for sterile/no-touch environments
  - **Industrial/Security** — kiosk-style access and monitoring workflows
- **Gesture-based attendance system** — register students/users by gesture, track check-ins in a local SQLite database, and trigger real-time notifications
- **Notification engine** — sends webhook alerts (Slack/Discord-compatible) on attendance events
- **Floating "Always on Top" camera window** so you can see gesture status while using other apps
- **Local-first & private** — all video processing happens on-device; nothing is uploaded

---

## 🏗️ Architecture

```
                        Webcam
                          │
                          ▼
              ┌─────────────────────┐
              │   GestureEngine     │  (gesture_engine.py) – MediaPipe hand landmark detection
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │  Gesture Matching    │  gestures.json / sequences.json – trained gesture profiles
              └──────────┬──────────┘
                         ▼
        ┌────────────────┴─────────────────┐
        ▼                                  ▼
┌───────────────┐                 ┌─────────────────────┐
│  ActionMap    │                 │  AttendanceManager    │
│ (action_map.py)│                │ (attendance_manager.py)│
│ Keyboard/mouse/│                │ SQLite check-in log    │
│ app-specific   │                └───────────┬─────────┘
│ actions, voice │                            ▼
│ (voice_engine) │                 ┌─────────────────────┐
└───────────────┘                  │ NotificationEngine    │
                                    │ (webhook alerts)      │
                                    └─────────────────────┘

        All orchestrated by a Flask server (server.py)
        rendered inside a pywebview desktop window (desktop_app.py)
        Frontend: HTML/CSS/JS control panel (frontend/)
```

---

## 📁 Project Structure

```
hand-gesture-control/
├── desktop_app.py             # Desktop window entry point (pywebview wrapper)
├── server.py                  # Flask backend — camera stream, gesture state, API routes
├── config.py                  # Camera, model, and gesture-logic configuration
├── gesture_engine.py           # MediaPipe hand landmark detection & gesture classification
├── action_map.py                # Maps gestures to keyboard/mouse/app actions, per-app profiles
├── attendance_manager.py         # SQLite-based gesture attendance tracking
├── notification_engine.py         # Webhook-based real-time alerts
├── voice_engine.py                 # Speech recognition for voice commands
├── augmentation_utils.py            # Image augmentation for gesture training data
├── draw_utils.py                     # Landmark/overlay drawing utilities
├── action_config.json                 # Saved action-mapping profiles
├── gestures.json                       # Trained gesture definitions
├── sequences.json                       # Trained gesture sequence definitions
├── hand_landmarker.task                  # MediaPipe hand landmark model
├── attendance.db                          # SQLite database (attendance records)
├── frontend/                               # Browser-based control panel
│   ├── index.html / home.html               # Main dashboard
│   ├── hub.html                               # General control hub
│   ├── admin.html                              # Gesture/action administration
│   ├── attendance.html                          # Attendance dashboard
│   ├── presentation.html                         # Presentation remote mode
│   ├── medical.html                               # Medical/no-touch mode
│   ├── security.html                               # Security/kiosk mode
│   ├── drive.html                                   # Virtual mouse ("drive") mode
│   ├── float.html / float_script.js / float_style.css  # Floating always-on-top camera view
│   └── script.js / style.css                          # Shared frontend logic & styling
├── samples/                                 # Captured gesture training images
├── scratch/test_mapping.py                    # Ad-hoc test script for action mapping
├── DEPLOYMENT.md                                # Production/real-world deployment guide
├── start_app.bat / start_linux.sh                # App launch scripts
├── install_requirements.bat                        # Windows dependency installer
└── requirements.txt                                # Python dependencies
```

---

## ⚙️ Requirements

- Python 3.8+
- A working webcam
- Windows 10/11 recommended for full desktop automation support (a Linux launch script is also included)

Key dependencies (see `requirements.txt`):

- [`mediapipe`](https://pypi.org/project/mediapipe/) — hand landmark detection
- [`opencv-python`](https://pypi.org/project/opencv-python/) — camera capture & image processing
- [`pyautogui`](https://pypi.org/project/pyautogui/) — desktop automation (mouse/keyboard)
- [`flask`](https://pypi.org/project/Flask/) & `flask-cors` — backend server
- [`pywebview`](https://pypi.org/project/pywebview/) — native desktop window wrapper
- [`SpeechRecognition`](https://pypi.org/project/SpeechRecognition/) — voice command engine
- `pywin32`, `psutil` — active-window detection for per-app action profiles (Windows)
- `pypdf` — PDF utilities used by certain actions
- `numpy`, `requests`

---

## 🚀 Installation & Setup

```bash
# Clone the repository
git clone https://github.com/Aman130901/-hand-gesture-control.git
cd -hand-gesture-control

# Install dependencies
pip install -r requirements.txt
```

On Windows, you can instead double-click **`install_requirements.bat`** to install everything automatically.

> If you hit permission errors during install, try running the terminal as Administrator.

---

## ▶️ How to Run

**Easiest way (Windows):** double-click **`start_app.bat`** — this launches the Flask backend and opens the desktop app window automatically.

**Linux:** run `./start_linux.sh`.

**Manual start (any platform):**

```bash
python desktop_app.py
```

This starts the Flask server in a background thread and opens the app in a native `pywebview` window pointed at the local server.

---

## 🎮 How to Use

1. **Detection Mode** — the app starts tracking your hand immediately:
   - **Point** → move the mouse cursor
   - **Pinch (index + thumb)** → left click / drag
   - **Pinch (middle + thumb)** → right click
2. **Train custom gestures** — open the admin/training panel, show a gesture to the camera, and record samples. Live feedback shows brightness, hand size, and angle to help you capture consistent samples.
3. **Map gestures to actions** — assign each trained gesture to a keyboard shortcut, media control, or app-specific action. Action profiles can be scoped to the currently active application.
4. **Switch domains** — choose Hub, Presentation, Medical, Security, or Attendance mode from the frontend to change the available actions and UI for that context.
5. **Floating window** — click the float button to detach the camera preview into an always-on-top window while you work in other apps.
6. **Attendance mode** — register users by gesture once; afterward, showing that gesture logs a timestamped check-in to the local SQLite database and can trigger a webhook notification.

---

## 🩺 Domain Modes

| Domain | Frontend Page | Use Case |
|---|---|---|
| Hub | `hub.html` | General-purpose desktop control |
| Presentation | `presentation.html` | Hands-free slide navigation |
| Medical | `medical.html` | No-touch control for clinical settings |
| Security | `security.html` | Kiosk-style access control |
| Attendance | `attendance.html` | Gesture-based check-in tracking |
| Admin | `admin.html` | Gesture training & action configuration |
| Drive | `drive.html` | Virtual mouse mode |

---

## ❓ Troubleshooting

- **Camera not opening?** Make sure no other app (Zoom, Teams) is using the webcam, and check `CAMERA_INDEX` in `config.py` if you have multiple cameras.
- **Gestures not triggering reliably?** Ensure good, even lighting, and retrain the gesture if detection feels inconsistent. `GESTURE_STABILITY_FRAMES` and `MIN_HAND_DETECTION_CONFIDENCE` in `config.py` can be tuned for your hardware.
- **Mouse not moving?** Confirm "Virtual Mouse" / Drive mode is active.
- **Voice commands not responding?** Check microphone permissions and that `SpeechRecognition` installed correctly (it depends on PyAudio on some platforms).

For production/kiosk deployment guidance (hardware selection, mounting, auto-start, and maintenance), see [`DEPLOYMENT.md`](./DEPLOYMENT.md).

---

## 🔒 Privacy

All hand-tracking and gesture recognition runs locally on-device. No video is uploaded or stored — only trained gesture landmark data and, in Attendance mode, check-in timestamps, are persisted locally.

---

## 📜 License

This project is open source. Feel free to modify and distribute — see the LICENSE file for details.

---

## 👤 Author

**Aman Sonkar**
