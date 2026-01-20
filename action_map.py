import pyautogui
import json
import os
import subprocess
import ctypes
import time
import math
import tkinter as tk
from tkinter import filedialog, simpledialog
from urllib.parse import quote
from pypdf import PdfReader, PdfWriter
from voice_engine import VoiceEngine

class ActionMap:
    def __init__(self, config_file="action_config.json"):
        self.config_file = config_file
        self.mapping = self.load_mapping()
        self.voice_engine = VoiceEngine()
        
        # Configuration for pyautogui
        pyautogui.FAILSAFE = False # Prevent fail-safe corner triggers which can be annoying with hand tracking
        self.screen_w, self.screen_h = pyautogui.size()
        
        # Smoothing for mouse
        self.prev_x, self.prev_y = 0, 0
        self.smooth_factor = 0.2 # Lower = smoother but more lag
        
        # Smart Mouse State
        self.is_left_clicked = False
        self.last_right_click_time = 0

    def load_mapping(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default if no config
        default_map = {
            "fist": "volume_mute",
            "open_palm": "play_pause",
            "peace": "screenshot",
            "thumbs_up": "volume_up",
            "thumbs_down": "volume_down"
        }
        # Save default
        with open(self.config_file, 'w') as f:
            json.dump(default_map, f, indent=4)
        return default_map

    def map_gesture(self, gesture_name, action_name):
        self.mapping[gesture_name] = action_name
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.mapping, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving mapping: {e}")
            return False

    def rename_mapping(self, old_gesture, new_gesture):
        if old_gesture in self.mapping:
            action = self.mapping.pop(old_gesture)
            self.mapping[new_gesture] = action
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(self.mapping, f, indent=4)
                return True
            except Exception as e:
                print(f"Error saving mapping rename: {e}")
                return False
        return True # Return true if old mapping didn't exist (nothing to do)

    # --- Media ---
    def _action_media_play_pause(self): pyautogui.press('playpause')
    def _action_media_stop(self): pyautogui.press('stop')
    def _action_media_next(self): pyautogui.press('nexttrack')
    def _action_media_prev(self): pyautogui.press('prevtrack')
    def _action_volume_mute(self): pyautogui.press('volumemute')
    def _action_volume_up(self): pyautogui.press('volumeup')
    def _action_volume_down(self): pyautogui.press('volumedown')

    # --- Browser ---
    def _action_browser_new_tab(self): pyautogui.hotkey('ctrl', 't')
    def _action_browser_close_tab(self): pyautogui.hotkey('ctrl', 'w')
    def _action_browser_reopen_tab(self): pyautogui.hotkey('ctrl', 'shift', 't')
    def _action_browser_next_tab(self): pyautogui.hotkey('ctrl', 'tab')
    def _action_browser_prev_tab(self): pyautogui.hotkey('ctrl', 'shift', 'tab')
    def _action_browser_refresh(self): pyautogui.hotkey('ctrl', 'r')
    def _action_browser_history(self): pyautogui.hotkey('ctrl', 'h')
    def _action_browser_downloads(self): pyautogui.hotkey('ctrl', 'j')

    # --- Productivity ---
    def _action_copy(self): pyautogui.hotkey('ctrl', 'c')
    def _action_paste(self): pyautogui.hotkey('ctrl', 'v')
    def _action_cut(self): pyautogui.hotkey('ctrl', 'x')
    def _action_undo(self): pyautogui.hotkey('ctrl', 'z')
    def _action_redo(self): pyautogui.hotkey('ctrl', 'y')
    def _action_select_all(self): pyautogui.hotkey('ctrl', 'a')
    def _action_save(self): pyautogui.hotkey('ctrl', 's')
    def _action_print(self): pyautogui.hotkey('ctrl', 'p')
    def _action_zoom_in(self): pyautogui.hotkey('ctrl', '+')
    def _action_zoom_out(self): pyautogui.hotkey('ctrl', '-')

    # --- Navigation ---
    def _action_scroll_up(self): pyautogui.scroll(40)
    def _action_scroll_down(self): pyautogui.scroll(-40)
    
    def _action_dynamic_scroll(self, landmarks):
        if not landmarks: return
        # Use Index Finger Tip (8)
        y = landmarks[8].y
        
        # Deadzone 0.4 - 0.6
        scroll_amount = 0
        if y < 0.4: # Top of screen -> Scroll Up
            dist = 0.4 - y
            scroll_amount = int(dist * 400) # Max ~160
        elif y > 0.6: # Bottom of screen -> Scroll Down
            dist = y - 0.6
            scroll_amount = -int(dist * 400)
            
        if scroll_amount != 0:
            pyautogui.scroll(scroll_amount)

    def _action_page_up(self): pyautogui.press('pageup')
    def _action_page_down(self): pyautogui.press('pagedown')
    def _action_arrow_up(self): pyautogui.press('up')
    def _action_arrow_down(self): pyautogui.press('down')
    def _action_arrow_left(self): pyautogui.press('left')
    def _action_arrow_right(self): pyautogui.press('right')

    # --- Window Management ---
    def _action_minimize_window(self): pyautogui.hotkey('win', 'down')
    def _action_maximize_window(self): pyautogui.hotkey('win', 'up')
    def _action_restore_window(self): pyautogui.hotkey('win', 'shift', 'up') # Or down usually works to restore from max
    def _action_close_current_window(self): pyautogui.hotkey('alt', 'f4')
    def _action_alt_tab(self): pyautogui.hotkey('alt', 'tab')
    def _action_win_tab(self): pyautogui.hotkey('win', 'tab')
    def _action_show_desktop(self): pyautogui.hotkey('win', 'd')

    # --- Mouse ---
    def _action_left_click(self): pyautogui.click()
    def _action_right_click(self): pyautogui.click(button='right')
    def _action_middle_click(self): pyautogui.click(button='middle')
    def _action_double_click(self): pyautogui.doubleClick()

    def _action_track_cursor(self, landmarks):
        if not landmarks: return
        # Index finger tip is 8
        tip = landmarks[8]
        
        # Mapping coordinates 0-1 to screen pixels
        # Direct x mapping (0->0, 1->1) for mirrored feed logic
        target_x = tip.x * self.screen_w
        target_y = tip.y * self.screen_h
        
        # Smoothing
        self.prev_x = self.prev_x * self.smooth_factor + target_x * (1 - self.smooth_factor)
        self.prev_y = self.prev_y * self.smooth_factor + target_y * (1 - self.smooth_factor)
        
        pyautogui.moveTo(self.prev_x, self.prev_y)

    # --- Smart Mouse v2 ---
    def _action_smart_mouse(self, landmarks):
        if not landmarks: return
        
        # Landmarks:
        # 4 = Thumb Tip, 8 = Index Tip
        # 5 = Index MCP (Base of Index), 2 = Thumb MCP
        
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        index_mcp = landmarks[5]
        
        # Helper for distance (normalized coords)
        def dist(p1, p2):
            return math.hypot(p1.x - p2.x, p1.y - p2.y)
            
        # 1. Logic Definitions
        # "Close Thumb" -> Thumb Tip (4) close to Index Base (5)
        thumb_closed_dist = dist(thumb_tip, index_mcp)
        
        # "Close Only Index" -> Index Tip (8) curled down to MCP (5)
        index_closed_dist = dist(index_tip, index_mcp)
        
        # Thresholds
        CLICK_THRESHOLD = 0.1
        
        # 2. Right Click Logic: "Close Only Index"
        # Condition: Index is curled AND Thumb is NOT curled (open)
        if index_closed_dist < CLICK_THRESHOLD and thumb_closed_dist > CLICK_THRESHOLD:
            # Ensure Left Click is released if we switch to Right Click (safety)
            if self.is_left_clicked:
                pyautogui.mouseUp()
                self.is_left_clicked = False

            current_time = time.time()
            if current_time - self.last_right_click_time > 1.0: # Cooldown
                pyautogui.click(button='right')
                self.last_right_click_time = current_time
            # Locking cursor while clicking prevents jitter
            return 

        # 3. Left Click Logic: "Close Thumb"
        # Condition: Thumb is curled (Index should be open usually for tracking)
        is_thumb_closed = thumb_closed_dist < CLICK_THRESHOLD
        
        if is_thumb_closed:
            if not self.is_left_clicked:
                pyautogui.mouseDown()
                self.is_left_clicked = True
        else:
            if self.is_left_clicked:
                pyautogui.mouseUp()
                self.is_left_clicked = False

        # 4. Cursor Tracking
        # Only track if not right-clicking (which we returned from already)
        self._action_track_cursor(landmarks)

    def is_continuous(self, gesture_name):
        action = self.mapping.get(gesture_name)
        if not action: return False
        return action in ["track_cursor", "smart_mouse", "scroll_up", "scroll_down", "volume_up", "volume_down", "dynamic_scroll"]

    # --- System ---
    def _action_screenshot(self): pyautogui.hotkey('win', 'printscreen')
    def _action_lock_screen(self): ctypes.windll.user32.LockWorkStation()
    def _action_task_manager(self): pyautogui.hotkey('ctrl', 'shift', 'esc')
    def _action_file_explorer(self): pyautogui.hotkey('win', 'e')
    def _action_settings(self): pyautogui.hotkey('win', 'i')
    def _action_enter(self): pyautogui.press('enter')
    def _action_space(self): pyautogui.press('space')
    def _action_esc(self): pyautogui.press('esc')
    def _action_backspace(self): pyautogui.press('backspace')
    def _action_tab(self): pyautogui.press('tab')

    # --- Window Snapping ---
    def _action_snap_window_left(self): pyautogui.hotkey('win', 'left')
    def _action_snap_window_right(self): pyautogui.hotkey('win', 'right')
    
    # --- Virtual Desktops ---
    def _action_desktop_next(self): pyautogui.hotkey('win', 'ctrl', 'right')
    def _action_desktop_prev(self): pyautogui.hotkey('win', 'ctrl', 'left')
    def _action_desktop_new(self): pyautogui.hotkey('win', 'ctrl', 'd')
    def _action_desktop_close(self): pyautogui.hotkey('win', 'ctrl', 'f4')

    # --- System Tools ---
    def _action_open_start_menu(self): pyautogui.press('win')
    def _action_emoji_panel(self): pyautogui.hotkey('win', '.')
    def _action_clipboard_history(self): pyautogui.hotkey('win', 'v')
    def _action_run_dialog(self): pyautogui.hotkey('win', 'r')
    
    # --- Browser Extra ---
    def _action_browser_focus_address(self): pyautogui.hotkey('alt', 'd')

    # --- PowerPoint ---
    def _action_ppt_next(self): pyautogui.press('right')
    def _action_ppt_prev(self): pyautogui.press('left')
    def _action_ppt_start(self): pyautogui.press('f5')
    def _action_ppt_stop(self): pyautogui.press('esc')
    def _action_ppt_black_screen(self): pyautogui.press('b')
    def _action_ppt_white_screen(self): pyautogui.press('w')
    def _action_ppt_laser_pointer(self): pyautogui.hotkey('ctrl', 'l')
    def _action_ppt_pen(self): pyautogui.hotkey('ctrl', 'p')

    # --- Word / Document ---
    def _action_word_bold(self): pyautogui.hotkey('ctrl', 'b')
    def _action_word_italic(self): pyautogui.hotkey('ctrl', 'i')
    def _action_word_underline(self): pyautogui.hotkey('ctrl', 'u')
    def _action_word_align_center(self): pyautogui.hotkey('ctrl', 'e')
    def _action_word_align_left(self): pyautogui.hotkey('ctrl', 'l')
    def _action_word_align_right(self): pyautogui.hotkey('ctrl', 'r')

    # --- System Power ---
    def _action_shutdown(self): 
        # Non-blocking shutdown command
        subprocess.Popen("shutdown /s /t 60", shell=True) 
    def _action_restart(self): 
        subprocess.Popen("shutdown /r /t 60", shell=True)
    def _action_sleep(self):
        # Sleep is inherently blocking in some ways but this is the best we can do
        subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)

    # --- App Launchers ---
    def _action_open_calculator(self): subprocess.Popen("calc", shell=True)
    def _action_open_notepad(self): subprocess.Popen("notepad", shell=True)
    def _action_open_cmd(self): subprocess.Popen("start cmd", shell=True)
    
    # --- PDF Tools ---
    def _action_split_pdf(self):
        """
        Signals to the frontend that a PDF split UI should be shown.
        Actual processing happens via a separate API call.
        """
        # We just return the action name, the server/frontend will handle the rest.
        return "split_pdf"

    # --- Voice Typing ---
    def _action_voice_type(self):
        # Run in a separate thread so we don't block the main loop
        import threading
        t = threading.Thread(target=self.voice_engine.listen_and_type)
        t.daemon = True
        t.start()
    
    # --- Custom Logic Helpers ---
    def _execute_type_text(self, text):
        pyautogui.write(text, interval=0.05)
    
    def _execute_custom_cmd(self, cmd):
        # clean command
        cmd = cmd.strip()
        lower_cmd = cmd.lower()
        
        print(f"[DEBUG] Custom Command: {cmd}")

        import webbrowser
        import re
        import shutil

        # Helper to get specific browser controller
        def get_browser(txt):
            try:
                if 'chrome' in txt:
                    return webbrowser.get('google-chrome')
                if 'edge' in txt:
                    return webbrowser.get('windows-default') 
                if 'firefox' in txt:
                    return webbrowser.get('firefox')
            except:
                return None
            return None

        # 1. URL Detection (Prioritize explicit URLs)
        if re.match(r'^(http|www\.|[a-z0-9]+\.[a-z]{2,})', lower_cmd):
             if not lower_cmd.startswith('http'):
                 url = 'https://' + cmd
             else:
                 url = cmd
             webbrowser.open(url)
             return True

        # 2. Logic for "Close [target]"
        if lower_cmd.startswith("close ") or lower_cmd.startswith("exit ") or lower_cmd.startswith("kill "):
            # Extract target
            if lower_cmd.startswith("close"): target = lower_cmd[6:].strip()
            elif lower_cmd.startswith("exit"): target = lower_cmd[5:].strip()
            else: target = lower_cmd[5:].strip()
            
            # Map friendly names to Process Names (.exe)
            # Use 'tasklist' manually to find these if unsure, but standard ones are:
            proc_map = {
                "chrome": "chrome.exe",
                "google chrome": "chrome.exe",
                "browser": "chrome.exe",
                "firefox": "firefox.exe",
                "edge": "msedge.exe",
                "microsoft edge": "msedge.exe",
                "notepad": "notepad.exe",
                "calculator": "CalculatorApp.exe",
                "calc": "CalculatorApp.exe",
                "whatsapp": "WhatsApp.exe",
                "spotify": "Spotify.exe",
                "vlc": "vlc.exe",
                "media player": "vlc.exe",
                "word": "WINWORD.EXE",
                "winword": "WINWORD.EXE",
                "microsoft word": "WINWORD.EXE",
                "excel": "EXCEL.EXE",
                "microsoft excel": "EXCEL.EXE",
                "powerpoint": "POWERPNT.EXE",
                "ppt": "POWERPNT.EXE",
                "microsoft powerpoint": "POWERPNT.EXE",
                "vs code": "Code.exe",
                "vscode": "Code.exe",
                "code": "Code.exe",
                "teams": "Teams.exe",
                "microsoft teams": "Teams.exe",
                "slack": "slack.exe",
                "discord": "Discord.exe",
                "zoom": "Zoom.exe",
                "paint": "mspaint.exe",
                "settings": "SystemSettings.exe",
                "explorer": "explorer.exe",
                "file explorer": "explorer.exe",
                "cmd": "cmd.exe",
                "command prompt": "cmd.exe",
                "powershell": "powershell.exe",
                "task manager": "Taskmgr.exe",
                # UWP Apps (Tricky, sometimes hosted in ApplicationFrameHost, but often have specific exe)
                "store": "WinStore.App.exe",
                "microsoft store": "WinStore.App.exe",
                "photos": "Microsoft.Photos.exe",
                "camera": "WindowsCamera.exe",
                "snipping tool": "SnippingTool.exe"
            }
            
            # Get process name
            proc_name = proc_map.get(target)
            
            # If not in map, try using the target as the process name directly (heuristic)
            if not proc_name:
                # If valid text, assume .exe
                if " " not in target:
                    proc_name = f"{target}.exe"
            
            if proc_name:
                print(f"[INFO] Closing process: {proc_name}")
                # /IM = Image Name, /F = Force
                try:
                    subprocess.Popen(f"taskkill /IM {proc_name} /F", shell=True)
                    return True
                except Exception as e:
                    print(f"Error closing {proc_name}: {e}")
            
            # If we couldn't even guess a process name (e.g. multi-word unknown app), 
            # maybe do nothing or inform? 
            # For now, if unknown, we just return True to avoid fallback to Search.
            return True


        # 3. Logic for "Open [target] in [browser]"
        browser_pref = None
        if "in google chrome" in lower_cmd or "in chrome" in lower_cmd:
            browser_pref = get_browser("chrome")
        elif "in firefox" in lower_cmd:
             browser_pref = get_browser("firefox")
        elif "in edge" in lower_cmd:
             browser_pref = get_browser("edge")
        
        clean_cmd = lower_cmd
        clean_cmd = re.sub(r'\s+in\s+(google\s+)?chrome', '', clean_cmd)
        clean_cmd = re.sub(r'\s+in\s+firefox', '', clean_cmd)
        clean_cmd = re.sub(r'\s+in\s+(microsoft\s+)?edge', '', clean_cmd)
        clean_cmd = re.sub(r'\s+in\s+browser', '', clean_cmd)
        clean_cmd = clean_cmd.strip()

        # 3. Handle "Open [target]" or just "[target]"
        target = clean_cmd
        if clean_cmd.startswith("open "):
            target = clean_cmd[5:].strip()

        # Shortcuts (Mixed Web/App)
        # For apps that have a web version, we list the LOCAL protocol first or just the name.
        # Logic below will try local first, then fallback to web if defined.
        shortcuts = {
            "youtube": "https://youtube.com",
            "google": "https://google.com",
            "facebook": "https://facebook.com",
            "instagram": "https://instagram.com",
            "whatsapp": "whatsapp:", 
            "whatsapp web": "https://web.whatsapp.com", 
            "whatsweb": "https://web.whatsapp.com",
            "spotify": "spotify:", 
            "gmail": "https://mail.google.com",
            "chatgpt": "https://chatgpt.com",
            
            # Dev Tools
            "vs code": "code",
            "vscode": "code",
            "code": "code",
            "cmd": "cmd",
            "command prompt": "cmd",
            "powershell": "powershell",

            # Office
            "word": "winword",
            "microsoft word": "winword",
            "excel": "excel",
            "microsoft excel": "excel",
            "powerpoint": "powerpnt",
            "ppt": "powerpnt",
            "microsoft powerpoint": "powerpnt",
            
            # Utilities
            "calculator": "calc",
            "calc": "calc",
            "notepad": "notepad",
            "paint": "mspaint",
            "explorer": "explorer",
            "file explorer": "explorer",
            "task manager": "taskmgr",
            "snipping tool": "snippingtool",

            # Windows Settings / UWP using Protocols (Safest way to launch)
            "settings": "ms-settings:",
            "store": "ms-windows-store:",
            "app store": "ms-windows-store:",
            "microsoft store": "ms-windows-store:", 
            "ms store": "ms-windows-store:",
            "camera": "microsoft.windows.camera:",
            "photos": "ms-photos:",
            "clock": "ms-clock:",
            "alarm": "ms-clock:",
            "todo": "ms-todo:",
            "weather": "bingweather:",
            "maps": "bingmaps:"
        }

        matched = shortcuts.get(target)

        # --- PATH A: User specified a browser ("in chrome") ---
        # STRICTLY Web Actions (URL or Search)
        if browser_pref:
             # If matched shortcut is a URL, use it
             if matched and matched.startswith("http"):
                 url = matched
             elif '.' in target and ' ' not in target:
                 url = 'https://' + target
             else:
                 # Fallback: Search
                 url = f"https://www.google.com/search?q={quote(target)}"
            
             browser_pref.open(url)
             return True

        # --- PATH B: No browser specified (Local App preferred) ---
        
        # Helper to launch and detect failure
        def try_launch_local(cmd):
            try:
                # STRATEGY: Use PowerShell Start-Process to force focus.
                # os.startfile often launches in background if Python doesn't have focus.
                # We also minimize the current window (Python/Console) momentarily maybe? No that's jarring.
                
                # Trick: Send an 'Alt' key press to wake up the UI thread? 
                # Better: Use PowerShell.
                
                # Handling shortcuts (protocols or paths) vs raw commands
                
                # 1. Try PowerShell Start-Process (most robust for Focus)
                # We use -PassThru to check existence? No, just run it.
                # Quotes are tricky.
                
                safe_cmd = cmd.replace("'", "''") # Escape for PS
                
                # "start" command in shell sometimes works better for focus than direct execution
                # But os.startfile is basically "start".
                
                # Let's try executing via 'start' explicitly in shell, which usually brings to front.
                # subprocess.Popen(f'start "" "{cmd}"', shell=True)
                
                # user reported background issue. Let's try the ForegroundLockTimeout trick? 
                # Or just use PowerShell which requests focus.
                
                # TRICK: Simulate "User Input" to bypass Windows ForegroundLockTimeout.
                # Windows prevents background apps from stealing focus unless user input is detected.
                # Pressing 'alt' is harmless (toggles menu bar) but resets the lock timer.
                try:
                    pyautogui.press('alt')
                except:
                    pass
                
                # Small delay to let Windows register the input
                # time.sleep(0.05) 

                ps_command = f"Start-Process '{safe_cmd}' -WindowStyle Normal"
                subprocess.Popen(["powershell", "-Command", ps_command], shell=True)
                
                return True
            except Exception as e:
                # print(f"DEBUG: PS Launch failed: {e}")
                # Fallback to os.startfile
                try:
                    os.startfile(cmd)
                    return True
                except:
                    return False

        # 1. Known Shortcut
        if matched:
            # If it's a web link, just open it (default browser)
            if matched.startswith("http"):
               webbrowser.open(matched)
               return True
            else:
               # Try local
               if try_launch_local(matched): return True

        # 2. Check if it's an executable in PATH (Old reliable)
        if shutil.which(target):
            if try_launch_local(target): return True

        # 3. Check for URL-like
        if '.' in target and ' ' not in target:
             webbrowser.open('https://' + target)
             return True
        
        # 4. Try generic local launch (The "If present, open it" rule)
        # Even if not in shortcut map, user might say "open figma".
        # os.startfile("figma") might work if "figma" is in path or registered.
        if try_launch_local(target):
             return True
        
        # 5. If "whatsapp" specifically failed local `whatsapp:` above (via shortcut),
        # maybe we should fallback to web version for convenience?
        if target == "whatsapp" or target == "spotify":
             # Special handling: User asked for app, app missing.
             # "sometime the app ... maynot be present ... perform the action"
             # Opening web version is a good fallback "action".
             if target == "whatsapp": webbrowser.open("https://web.whatsapp.com"); return True
             if target == "spotify": webbrowser.open("https://open.spotify.com"); return True
        
        # 6. ULTIMATE FALLBACK: Search Google
        print(f"[INFO] Command '{cmd}' fallback to Search")
        webbrowser.open(f"https://www.google.com/search?q={quote(cmd)}")
        return True

    def perform_action(self, action, landmarks=None):
        """
        Executes a specific action string directly.
        """
        # print(f"[DEBUG] Performing Action: '{action}'")
        
        if not action:
            return None

        # Check if it's a known method
        method_name = f"_action_{action}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            try:
                if action == "track_cursor" and landmarks:
                    method(landmarks)
                # Smart Mouse also needs landmarks
                elif action == "smart_mouse" and landmarks:
                    method(landmarks)
                else:
                    method()
                # print(f"[DEBUG] Executed {method_name}")
                return action
            except Exception as e:
                print(f"[ERROR] Execution failed for {method_name}: {e}")
                return None
        
        # Text Macro Handler
        if action.startswith("type:"):
            text = action[5:]
            self._execute_type_text(text)
            return f"Typed: {text}"

        # Custom Command Handler
        if action.startswith("cmd:"):
            command = action[4:]
            self._execute_custom_cmd(command)
            return f"CMD: {command}"
        
        # Backward compatibility
        if action == "play_pause": self._action_media_play_pause(); return "media_play_pause"
        
        print(f"[DEBUG] No handler found for action: {action}")
        return None

    def execute(self, gesture_name, landmarks=None):
        action = self.mapping.get(gesture_name)
        print(f"[DEBUG] Gesture: '{gesture_name}' -> Action: '{action}'")
        return self.perform_action(action, landmarks)

    def get_available_actions(self):
        return [
            # Media
            "media_play_pause", "media_stop", "media_next", "media_prev",
            "volume_mute", "volume_up", "volume_down",
            
            # Browser Control
            "browser_new_tab", "browser_close_tab", "browser_reopen_tab",
            "browser_next_tab", "browser_prev_tab", "browser_focus_address",
            "browser_refresh", "browser_history", "browser_downloads",
            
            # Productivity
            "copy", "paste", "cut", "undo", "redo",
            "select_all", "save", "print", "zoom_in", "zoom_out",
            
            # Presentation (PPT)
            "ppt_next", "ppt_prev", "ppt_start", "ppt_stop", 
            "ppt_black_screen", "ppt_white_screen", "ppt_laser_pointer", "ppt_pen",
            
            # Document (Word)
            "word_bold", "word_italic", "word_underline",
            "word_align_center", "word_align_left", "word_align_right",
            
            # Navigation
            "dynamic_scroll", "scroll_up", "scroll_down", "page_up", "page_down",
            "arrow_up", "arrow_down", "arrow_left", "arrow_right",
            
            # Window Management
            "snap_window_left", "snap_window_right",
            "minimize_window", "maximize_window", "restore_window", "close_current_window",
            "alt_tab", "win_tab", "show_desktop",
            "desktop_next", "desktop_prev", "desktop_new", "desktop_close",
            
            # Mouse
            "track_cursor", "left_click", "right_click", "double_click", "middle_click",
            
            # System
            "open_start_menu", "emoji_panel", "clipboard_history", "run_dialog",
            "screenshot", "lock_screen", "task_manager", "file_explorer", "settings",
            "enter", "space", "esc", "backspace", "tab",
            
            # Power & Apps
            "shutdown", "restart", "sleep",
            "open_calculator", "open_notepad", "open_cmd",
            
            # Advanced
            "custom_command", "type_text",
            
            # PDF
            "split_pdf",

            # Voice
            "voice_type"
        ]
