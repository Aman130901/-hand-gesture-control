import webview
import threading
import time
import sys
from server import app, logger, camera_loop, state

class DesktopApi:
    def __init__(self):
        self.float_window = None

    def toggle_floating_window(self):
        """Toggle the floating camera window."""
        if self.float_window:
            try:
                self.float_window.destroy()
            except:
                pass
            self.float_window = None
            logger.info("Closed Floating Window")
        else:
            # Create a small, frameless, always-on-top window
            width, height = 300, 200
            self.float_window = webview.create_window(
                'Float', 
                'http://127.0.0.1:5000/float',
                width=width,
                height=height,
                frameless=True,
                on_top=True,
                resizable=True,
                transparent=True, # Required for rounded corners
                min_size=(150, 100),
                easy_drag=False, # Disable built-in drag to prevent recursion error
                js_api=self, # Expose API to this window!
                x=0, y=0 # Will be positioned by OS or user
            )
            logger.info("Opened Floating Window")

api = DesktopApi()


def run_flask():
    """Run the Flask server."""
    logger.info("Starting Flask Server for Desktop App...")
    # We set use_reloader=False to avoid issues with double threads in a frozen or desktop context
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True, use_reloader=False)

def start_desktop():
    """Initialize and start the desktop window."""
    # Start the background camera thread (usually started in server.py's __main__, 
    # but we are importing 'app' so we need to start it manually here)
    logger.info("Starting Background Camera Thread for Desktop...")
    t_camera = threading.Thread(target=camera_loop, daemon=True)
    t_camera.start()

    # Start Flask in a background thread
    t_flask = threading.Thread(target=run_flask, daemon=True)
    t_flask.start()

    # Wait a moment for the server to start
    time.sleep(2)

    # Create the webview window
    window = webview.create_window(
        'Hand Gesture Control', 
        'http://127.0.0.1:5000',
        width=1280,
        height=850,
        min_size=(1000, 700),
        js_api=api
    )

    # Store window reference in state for pop-up functionality
    state.desktop_window = window

    logger.info("Launching Desktop Window...")
    # Enable debug=True to allow inspection and console access in the desktop app
    webview.start()

    # Clean shutdown logic
    logger.info("Closing Application...")
    state.camera_active = False # Signal camera loop to stop if possible
    sys.exit(0)

if __name__ == '__main__':
    start_desktop()
