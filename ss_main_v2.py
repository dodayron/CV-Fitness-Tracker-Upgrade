from picamera2 import Picamera2
import cv2
import mediapipe as mp
import numpy as np
import time

from datetime import datetime
from database import insert_session
import sound_manager

#screenshots temp code
from screenshot_manager import ScreenshotManager

# Importing from the v2 loader and LED manager
from exercise_loader_v2 import load_exercise
from led_manager import LEDManager

# Initialize MediaPipe
mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

# Load Initial Exercise
current_exercise = load_exercise("squat")

# track previous reps
previous_reps = 0;

# Initialise session_start so the first save works
session_start = datetime.now()

# Setup Camera (RPi)
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

#set LEDs 
leds = LEDManager()
leds.clear()

# FPS Calculation variables
p_time = 0

### SET THRESHOLD FOR LANDMARK DISPLAY
landmark_vis_thresh = 0.7

def draw_progress_bar(image, angle, ex_class):
    # Interpolate angle to bar height (normalized 0 to 1)
    # Mapping: Rest Angle (0%) -> Peak Angle (100%)
    # if statement to flip np.interp based on direction of exercise
    if ex_class.direction == "decrease":
        per = np.interp(angle, (ex_class.peak_thresh, ex_class.rest_thresh), (100, 0))
        bar = np.interp(angle, (ex_class.peak_thresh, ex_class.rest_thresh), (100, 400))
    else:
        per = np.interp(angle, (ex_class.rest_thresh, ex_class.peak_thresh), (0, 100))
        bar = np.interp(angle, (ex_class.rest_thresh, ex_class.peak_thresh), (400, 100))
    
    # Check if rep target reached for color change
    color = (0, 255, 255) # Yellow 
    if per == 100:
        color = (0, 255, 0) # Green if hit depth
    
    # Draw Bar background
    cv2.rectangle(image, (580, 100), (620, 400), (0, 255, 0), 1)
    # Draw Bar Fill
    cv2.rectangle(image, (580, int(bar)), (620, 400), color, cv2.FILLED)
    # Draw Percentage text
    cv2.putText(image, f'{int(per)}%', (565, 75), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

with mp_pose.Pose(min_detection_confidence=0.8, min_tracking_confidence=0.5, model_complexity=0) as pose:
    print("Starting Exercise Tracker V2... Press 'Esc' to quit.")
    # play start up sound
    sound_manager.start_sound.play()
    
    #screenshot init
    screenshots = ScreenshotManager (interval = 10)
    
    while True:
        try:
            # Capture frame
            frame = picam2.capture_array()
            
            # FPS Calculation
            c_time = time.time()
            fps = 1 / (c_time - p_time)
            p_time = c_time

            # MediaPipe Processing
            frame.flags.writeable = False 
            results = pose.process(frame)
            frame.flags.writeable = True

            # Draw Landmarks
            if results.pose_landmarks:
                
                # Logic Update
                angle = current_exercise.update(results.pose_landmarks.landmark)
                           
                landmarks = results.pose_landmarks.landmark
                #check average visibility before displaying on screen to avoid clutter
                '''
                avg_vis = sum(lm.visibility for lm in landmarks) / len(landmarks)
                if avg_vis > landmark_vis_thresh:'''
                mp_draw.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                    
                
            # Flip AFTER processing for display only
            frame = cv2.flip(frame, 1)
                

            ### UI Overlay ### (if landmarks detected)
            if results.pose_landmarks:
                # 1. Info Box Background
                cv2.rectangle(frame, (0,0), (180, 170), (245, 117, 16), -1)
                
                # 2. Text Data
                cv2.putText(frame, f"{current_exercise.name}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                cv2.putText(frame, str(current_exercise.reps), (10, 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 3)
                cv2.putText(frame, f"Stage: {current_exercise.stage}", (10, 130), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                
                cv2.putText(frame, f"FPS: {int(fps)}", (550, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0, 255), 2)

                # 3. In frame or not
                '''
                if avg_vis > landmark_vis_thresh:
                    cv2.putText(frame, "IN FRAME" , (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0) ,2)
                else:
                    cv2.putText(frame, "STEP BACK AND CENTER YOURSELF" , (40, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255) ,3)
    '''
                
                # 4. Progress Bar & Angle + sounds
                if angle is not None:
                    #on screen progress bar
                    draw_progress_bar(frame, angle, current_exercise)
                    if current_exercise.direction == "decrease":
                        #physical LED update
                        per = np.interp(angle, (current_exercise.peak_thresh, current_exercise.rest_thresh), (100,0))
                    else:
                        per = np.interp(angle, (current_exercise.rest_thresh, current_exercise.peak_thresh), (0,100))

                    
                    leds.update_bar(per)
                    leds.update_reps(current_exercise.reps)
                if current_exercise.reps > previous_reps:
                    # Check if it's the 8th nultiple rep
                    if current_exercise.reps % 8 == 0 and current_exercise.reps > 0:
                        sound_manager.chimes.play() 
                    else:
                        sound_manager.rep_beep.play()
                    
                    # Update tracker
                    previous_reps = current_exercise.reps
                    
                    
                '''##debugg temporary for landmark detection
                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
                    elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
                    wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value]
                    cv2.putText(frame, f"S:{shoulder.y:.2f} E:{elbow.y:.2f} W:{wrist.y:.2f}",
                        (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                    if angle is not None:
                        cv2.putText(frame, f"Angle: {int(angle)}", 
                            (10, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)
                    # also show the arm_raised check result directly
                    cv2.putText(frame, f"E<S: {elbow.y < shoulder.y} | W>=E-0.05: {wrist.y >= elbow.y - 0.05}",
                        (10, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
                '''
                    
            ######## Key Controls #######
            key = cv2.waitKey(1) & 0xFF
            
            # copy paste an exercise block and set new key press 
            # and call correst JSON file for new exercise
            # SQUAT
            if key == ord('1'):
                # END current session
                session_end = datetime.now()
                previous_reps = 0;

                insert_session(
                    exercise = current_exercise.name,
                    reps = current_exercise.reps,
                    sets = 1, # only one for now
                    date = session_start.strftime("%Y-%m-%d"), 
                    #strftime converts datetime to string to match the SQLite storage format
                    start_time = session_start.strftime("%H:%M:%S"),
                    end_time = session_end.strftime("%H:%M:%S")
                )
                
                sound_manager.squat_instruct.play()                
                current_exercise = load_exercise("squat")
                current_exercise.reps = 0 
            
            # RIGHT CURL
            elif key == ord('2'):
                # END current session
                session_end = datetime.now()
                previous_reps = 0;

                insert_session(
                    exercise = current_exercise.name,
                    reps = current_exercise.reps,
                    sets = 1,
                    date = session_start.strftime("%Y-%m-%d"),
                    start_time = session_start.strftime("%H:%M:%S"),
                    end_time = session_end.strftime("%H:%M:%S")
                )

                # START new session
                sound_manager.rCurl_instruct.play()
                current_exercise = load_exercise("curl_right")
                session_start = datetime.now()
            
            # LEFT CURL
            elif key == ord('3'):
                # END current session
                session_end = datetime.now()
                previous_reps = 0;

                insert_session(
                    exercise = current_exercise.name,
                    reps = current_exercise.reps,
                    sets = 1,
                    date = session_start.strftime("%Y-%m-%d"),
                    start_time = session_start.strftime("%H:%M:%S"),
                    end_time = session_end.strftime("%H:%M:%S")
                )
                
                sound_manager.lCurl_instruct.play()
                current_exercise = load_exercise("curl_left")
                current_exercise.reps = 0
                
            #LATERAL RAISE
            elif key == ord('4'):
                # END current session
                session_end = datetime.now()
                previous_reps = 0;

                insert_session(
                    exercise = current_exercise.name,
                    reps = current_exercise.reps,
                    sets = 1,
                    date = session_start.strftime("%Y-%m-%d"),
                    start_time = session_start.strftime("%H:%M:%S"),
                    end_time = session_end.strftime("%H:%M:%S")
                )
                
                sound_manager.rLat_instruct.play()
                current_exercise = load_exercise("lat_raise_right")
                current_exercise.reps = 0
                
            #end all
            elif key == 27: # ESC
                session_end = datetime.now()
                leds.clear()

                insert_session(
                    exercise=current_exercise.name,
                    reps=current_exercise.reps,
                    sets=1,
                    date=session_start.strftime("%Y-%m-%d"),
                    start_time=session_start.strftime("%H:%M:%S"),
                    end_time=session_end.strftime("%H:%M:%S")
                )
                break
            
            # Show Feed
            cv2.imshow("RPi Fitness Tracker V2", frame)
            #set full screen or not
     #       cv2.setWindowProperty("RPi Fitness Tracker V2", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            
            #screenshot
            screenshots.update(frame, key)
            
        except Exception as e:
            print(f"Error: {e}")
            leds.clear() #turn off leds if crash
            sound_manager.sound_quit() #turn off audio manager
            break

cv2.destroyAllWindows()
picam2.stop()
