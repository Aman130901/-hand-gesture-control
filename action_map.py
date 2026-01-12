import pyautogui
import json
import os
import subprocess
import ctypes
import time
import math
import tkinter as tk
from tkinter import filedialog, simpledialog
from pypdf import PdfReader, PdfWriter

class ActionMap:
    def __init__(self, config_file="action_config.json"):
        self.config_file = config_file
        self.mapping = self.load_mapping()
        
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
        # Mirroring x for intuitive control
        target_x = (1.0 - tip.x) * self.screen_w
        target_y = tip.y * self.screen_h
        
        # Smoothing
        self.prev_x = self.prev_x * self.smooth_factor + target_x * (1 - self.smooth_factor)
        self.prev_y = self.prev_y * self.smooth_factor + target_y * (1 - self.smooth_factor)
        
        pyautogui.moveTo(self.prev_x, self.prev_y)

    # --- Smart Mouse ---
    def _action_smart_mouse(self, landmarks):
        if not landmarks: return
        
        # Landmarks
        thumb_tip = landmarks[4]
        index_mcp = landmarks[5] # Base of index finger
        index_tip = landmarks[8]
        middle_tip = landmarks[12] # Keep for reference if needed
        
        # Helper for distance
        def dist(p1, p2):
            return math.hypot(p1.x - p2.x, p1.y - p2.y)
            
        # Distances for Curls
        # Index Curl: Tip (8) close to MCP (5)
        index_curl_dist = dist(index_tip, index_mcp)
        # Thumb Curl: Tip (4) close to Index MCP (5)
        thumb_curl_dist = dist(thumb_tip, index_mcp)
        
        # Thresholds (Adjusted for curls)
        CURL_THRESHOLD = 0.1
        
        # 1. Right Click (Index Curl)
        # Priority: Check Right Click first. If Index is curled, we STOP tracking to avoid jitter.
        if index_curl_dist < CURL_THRESHOLD:
            # Ensure Left Click is released if we switch to Right Click (safety)
            if self.is_left_clicked:
                pyautogui.mouseUp()
                self.is_left_clicked = False
                
            current_time = time.time()
            if current_time - self.last_right_click_time > 1.0: # 1s Cooldown
                pyautogui.click(button='right')
                self.last_right_click_time = current_time
            return # <--- LOCK CURSOR (Step 2 is skipped)

        # 2. Track Cursor (Only if Index is NOT curled)
        self._action_track_cursor(landmarks)
            
        # 3. Left Click / Drag (Thumb Curl)
        if thumb_curl_dist < CURL_THRESHOLD:
            if not self.is_left_clicked:
                pyautogui.mouseDown()
                self.is_left_clicked = True
        else:
            if self.is_left_clicked:
                pyautogui.mouseUp()
                self.is_left_clicked = False

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
    
    # --- Custom Logic Helpers ---
    def _execute_type_text(self, text):
        pyautogui.write(text, interval=0.05)
    
    def _execute_custom_cmd(self, cmd):
        try:
            subprocess.Popen(cmd, shell=True)
            return True
        except Exception as e:
            print(f"Error running cmd '{cmd}': {e}")
            return False

    def execute(self, gesture_name, landmarks=None):
        action = self.mapping.get(gesture_name)
        
        # Debugging
        print(f"[DEBUG] Gesture: '{gesture_name}' -> Action: '{action}'")
        
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
                print(f"[DEBUG] Executed {method_name}")
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
            "split_pdf"
        ]
