# 🖐️ Hand Gesture Control System

A powerful, real-time hand gesture recognition system that allows you to control your Windows desktop using your hands. From volume control to virtual mouse navigation, this project turns your webcam into a sophisticated input device. Now featuring a professional **Training Dashboard** and **System HUD**.

---

## 🚀 Introduction

This project is a bridge between human movement and digital action. By leveraging advanced Computer Vision and Machine Learning, it tracks hand movements and translates them into system-level commands. Whether it's scrolling through a PDF, taking a screenshot, or moving your cursor, it's all handled through intuitive hand gestures.

## 🧠 The AI & Models: How it Works

This project utilizes a multi-stage approach to gesture recognition:

1.  **Hand Landmarking (CNN):** 
    *   The core detection is powered by **MediaPipe's Hand Landmarker**. 
    *   It uses a **Convolutional Neural Network (CNN)** to perform "Palm Detection" and "Hand Landmark Localization".
    *   It maps **21 distinct 3D landmarks** (joints) on your hand in real-time.

2.  **Gesture Classification (Geometric Engine):**
    *   Instead of a heavy RNN (Recurrent Neural Network) which is typically used for sequences, we use a **Custom Geometric Engine**.
    *   **Logic:** It calculates the **Euclidean Distance** between normalized angle vectors of your hand's joints. 
    *   **Efficiency:** This makes it extremely fast and allows users to record and save new gestures instantly without needing to retrain a heavy deep-learning model.

---

## 🛠️ Prerequisites

To run this project, you need:
-   **Python 3.10+**
-   A working **Webcam**.
-   **Windows OS** (Required for `pyautogui` and desktop automation).

---

## 📦 Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Aman130901/-hand-gesture-control.git
    cd -hand-gesture-control
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Core dependencies: `opencv-python`, `mediapipe`, `pyautogui`, `flask`, `pypdf`, `pywebview`.*

---

## 💻 VS Code Setup (Recommended)

To have the best development experience and ensure the project runs properly in VS Code:

### 1. Install Extensions
*   **Python (Microsoft)**
*   **Pylance** (Language Support)

### 2. Running the Project
1.  Open the project folder in VS Code.
2.  Open a terminal (`Ctrl + ~`).
3.  **Run the Application:**
    You only need to run one script which handles both the server and the desktop UI.
    ```bash
    python desktop_app.py
    ```
    *This will launch the Flask backend and open the Floating Camera Window automatically.*

---

## 🎮 How to Use

### 1. Dashboard & Controls
The application interface opens in your browser (default `http://localhost:5000`).
*   **Gestures Gallery:** View and manage your recorded gestures.
*   **Training Dashboard:** Visualize model metrics (Loss/Accuracy) and simulate training epochs.
*   **Settings:** Configure camera resolution and theme.

### 2. Recording Gestures
1.  Navigate to the **RECORD** tab in the UI (or press 'r').
2.  Hold your hand in the desired pose.
3.  Click **"Capture"** or press **Space**.
4.  Name your gesture (e.g., "Fist", "Peace").

### 3. Mapping Actions
1.  Go to the **MAPPING** tab.
2.  Select a gesture from the dropdown.
3.  Assign a system action (e.g., *Volume Up*, *Scroll Down*, *Virtual Mouse*, *Split PDF*).

### 4. Floating HUD
A small, always-on-top window shows your camera feed and detected gestures, so you can see what the AI sees while using other apps.

---

## ✨ Features
*   **Real-time Hand Tracking**: 60+ FPS performance.
*   **Custom Gesture Recording**: Create your own gestures in seconds.
*   **Glassmorphism UI**: Beautiful, modern dark-mode interface.
*   **Training Simulation**: Visual dashboard for model performance.
*   **Virtual Mouse**: Control your cursor with your index finger.

---

**Built with ❤️ by Aman.**
