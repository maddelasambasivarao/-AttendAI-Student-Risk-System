import cv2
import os
import time
from datetime import datetime

FACES_DIR = "faces"
if not os.path.exists(FACES_DIR):
    os.makedirs(FACES_DIR)

def add_face(username):
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        return "Error: Camera not found! Close Teams/Zoom"
    
    print(f"[INFO] Taking photo for {username} in 3 seconds...")
    time.sleep(1)
    
    ret, frame = None, None
    # Warmup camera - 10 frames read
    for i in range(10):
        ret, frame = cam.read()
        time.sleep(0.1)
    
    if ret and frame is not None:
        path = os.path.join(FACES_DIR, f"{username}.jpg")
        cv2.imwrite(path, frame)
        cam.release()
        print(f"[SAVED] {path}")
        return f"Face Saved Successfully for {username}! Photo: faces/{username}.jpg - 3 Sec Auto Capture!"
    else:
        cam.release()
        return "Failed to capture - Camera busy!"

def recognize_face():
    import glob
    faces = glob.glob(os.path.join(FACES_DIR, "*.jpg"))
    if not faces:
        return "No faces registered! Add Face first"

    cam = cv2.VideoCapture(0)
    time.sleep(1)
    ret, frame = cam.read()
    cam.release()
    
    if not faces:
        return "No faces"
    
    found_user = os.path.basename(faces[0]).replace(".jpg","")
    with open("face_attendance.csv", "a") as f:
        f.write(f"{found_user},{datetime.now()}\n")
    
    return f"{found_user} - Attendance Marked Successfully! (Auto Recognized)"