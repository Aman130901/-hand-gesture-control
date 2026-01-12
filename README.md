# 🖐️ Hand Gesture Control System

A powerful, real-time hand gesture recognition system that allows you to control your Windows desktop using your hands. From volume control to virtual mouse navigation, this project turns your webcam into a sophisticated input device.

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
-   **Windows OS** (for system-level actions via `pyautogui`).

---

## 📦 Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Aman130901/-hand-gesture-control.git
    cd -hand-gesture-control
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Dependencies include: `opencv-python`, `mediapipe`, `pyautogui`, `numpy`, `flask`, `flask-cors`.*

---

## 💻 VS Code Setup & Extensions

To have the best development experience and ensure the project runs properly in VS Code, install the following extensions:

### Required Extensions:
1.  **Python (Microsoft):** Essential for linting, debugging, and IntelliSense.
2.  **Pylance:** High-performance language support for Python.
3.  **Live Server:** To run the `frontend/index.html` seamlessly.
4.  **ESLint / Prettier:** To keep the frontend code clean.

### Steps to Run in VS Code:
1.  Open the project folder in VS Code.
2.  Open a terminal in VS Code (`Ctrl + ~`).
3.  Run the backend:
    ```bash
    python server.py
    ```
4.  Run the gesture engine:
    ```bash
    python main.py
    ```
5.  Open `frontend/index.html` and click **"Go Live"** at the bottom right of VS Code to view the control panel.

---

## 🎮 How to Use

1.  **Detect Mode (Default):** The app starts by looking for gestures you've already saved.
2.  **Record Mode:** 
    *   Press **'r'** to enter recording mode.
    *   Hold your hand in the desired gesture.
    *   Press **'s'** to name it, type the name, and hit **Enter**.
3.  **Map Actions:** 
    *   Once a gesture is saved, the app will prompt you to assign it an action (e.g., *Volume Up*, *Screenshot*, *Virtual Mouse*).
    *   Press the corresponding number key to map the action.

---

## ✨ Conclusion

The **Hand Gesture Control System** represents a shift towards more natural user interfaces. By combining the robustness of CNN-based hand tracking with a flexible geometric classification engine, it provides a highly customizable and responsive experience. It's not just a tool; it's a foundation for the future of touchless interaction.

---

**Built with ❤️ for the Developer Community.**
