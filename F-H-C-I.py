# Tracking and Moving the Curser in Box, Speech for All Operations in mode with Blink and Resized Camera Frame
import cv2
import pyautogui
import mediapipe as mp
import numpy as np
import mouse
import multiprocessing
import speech_recognition as sr

# Initialize face mesh detector
face_mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)

# Screen dimensions
screen_w, screen_h = pyautogui.size()
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# Box dimensions (relative to the webcam frame size)
box_w = 200
box_h = 150
box_x = 220  # X position of the top-left corner of the box
box_y = 165  # Y position of the top-left corner of the box

# Eye landmark indices for detecting blinks
LEFT_EYE_INDICES = [145, 159]

# Threshold for detecting blinks
BLINK_THRESHOLD = 6.0

# Function for speech recognition
def speech_recognition_process(shared_state):
    recognizer = sr.Recognizer()
    while True:
        try:
            with sr.Microphone() as source:
                print("Listening for voice commands...")
                audio = recognizer.listen(source)
                recognized_query = recognizer.recognize_google(audio, language='en-in').lower()
                print(f"Recognized command: {recognized_query}")

                # Update the operation state
                if recognized_query in ["left click", "right click", "double click", "scroll up", "scroll down", "drag", "drop"]:
                    shared_state["operation_state"] = recognized_query
                    print(f"Operation state changed to: {recognized_query}")
        except sr.UnknownValueError:
            print("Could not understand audio.")
        except Exception as e:
            print(f"Speech recognition error: {e}")

# Function to map the landmark coordinates to screen coordinates
def map_landmark_to_screen(landmark, frame_w, frame_h):
    screen_x = np.interp(landmark.x * frame_w, [box_x, box_x + box_w], [0, screen_w])
    screen_y = np.interp(landmark.y * frame_h, [box_y, box_y + box_h], [0, screen_h])
    return screen_x, screen_y

# Function to detect eye blinks
def detect_blink(landmarks, frame_w, frame_h, eye_indices):
    eye_top = np.array([landmarks[eye_indices[0]].x * frame_w, landmarks[eye_indices[0]].y * frame_h])
    eye_bottom = np.array([landmarks[eye_indices[1]].x * frame_w, landmarks[eye_indices[1]].y * frame_h])
    distance = np.linalg.norm(eye_top - eye_bottom)
    return distance

# Function for video processing and mouse control
def video_processing_process(shared_state):
    cam = cv2.VideoCapture(0)
    delay = 0

    while True:
        # Capture frame from webcam
        _, frame = cam.read()
        frame = cv2.flip(frame, 1)  # Flip the frame horizontally for a mirror effect
        output = face_mesh.process(frame)  # Process the frame for face landmarks
        landmark_points = output.multi_face_landmarks  # Get the landmark points

        frame_h, frame_w, _ = frame.shape  # Get the frame dimensions

        # Draw the box on the frame
        cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), (255, 0, 0), 2)

        if landmark_points:
            landmarks = landmark_points[0].landmark

            # Get the nose tip landmark
            nose_tip = landmarks[1]

            # Map nose tip to screen coordinates
            x = int(nose_tip.x * frame_w)
            y = int(nose_tip.y * frame_h)
            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)  # Draw the nose tip

            # Check if the nose is within the box
            if box_x < x < box_x + box_w and box_y < y < box_y + box_h:
                # Move the cursor based on the nose tip position
                screen_x, screen_y = map_landmark_to_screen(nose_tip, frame_w, frame_h)
                mouse.move(screen_x, screen_y)

                # Detect blinks for left eye
                left_eye_blink_distance = detect_blink(landmarks, frame_w, frame_h, LEFT_EYE_INDICES)
               
                # Perform operations based on the operation state
                current_operation = shared_state["operation_state"]
                cv2.putText(frame, f"Mode: {current_operation}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

                if left_eye_blink_distance < BLINK_THRESHOLD and delay == 0:
                    if current_operation == "left click":
                        mouse.click(button="left")
                        print("Left Click")
                        pyautogui.sleep(1)
                    elif current_operation == "right click":
                        mouse.click(button="right")
                        print("Right Click")
                        pyautogui.sleep(1)
                    elif current_operation == "double click":
                        mouse.double_click(button="left")
                        print("Double Click")
                        pyautogui.sleep(1)
                    elif current_operation == "scroll up":
                        mouse.wheel(delta=-1)
                        print("Scroll Up")
                    elif current_operation == "scroll down":
                        mouse.wheel(delta=1)
                        print("Scroll Down")
                    elif current_operation == "drag":
                        pyautogui.mouseDown()  # Drag
                        print("Drag")
                    elif current_operation == "drop":
                        pyautogui.mouseUp()  # Drop
                        print("Drop")

        # Create a named window and set it to PiP mode
        window_name = "Facial Controlled Mouse with Voice Commands"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 320, 240)  # Resize the window for PiP (small window)
        cv2.moveWindow(window_name, screen_w - 340, screen_h - 300)  # Move to bottom-right corner
        # Display the video feed with landmarks and the box
        cv2.imshow(window_name, frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the webcam and close all OpenCV windows
    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Create a shared state dictionary for communication between processes
    with multiprocessing.Manager() as manager:
        shared_state = manager.dict()
        shared_state["operation_state"] = "left click"  # Initialize the state

        # Start processes
        speech_process = multiprocessing.Process(target=speech_recognition_process, args=(shared_state,))
        video_process = multiprocessing.Process(target=video_processing_process, args=(shared_state,))

        speech_process.start()
        video_process.start()

        # Wait for processes to finish
        speech_process.join()
        video_process.join()
        