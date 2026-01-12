import cv2
import time

def test_camera(index):
    print(f"Testing camera index {index}...")
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print(f"[-] Failed to open camera index {index}")
        return False
    
    ret, frame = cap.read()
    if ret:
        print(f"[+] Successfully read frame from camera index {index}")
        print(f"    Frame size: {frame.shape}")
        cv2.imwrite(f"test_frame_{index}.jpg", frame)
    else:
        print(f"[-] Opened camera {index} but failed to read frame")
    
    cap.release()
    return ret

print("Starting camera test...")
# Test indices 0, 1, 2
success = False
for i in range(3):
    if test_camera(i):
        success = True
        break

if not success:
    print("FATAL: Could not access any camera.")
else:
    print("Camera test passed.")
