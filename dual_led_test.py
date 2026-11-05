"""
dual_camera_fov_test.py
-----------------------
Captures from both Pi Camera modules simultaneously and displays
them side-by-side to demonstrate the FOV difference.

Requires both cameras connected to the Pi 5's two CSI ports.
Run with: python dual_camera_fov_test.py
Press ESC to quit.
"""

from picamera2 import Picamera2
import cv2
import numpy as np
import time

RESOLUTION = (640, 480)

# --- Initialise both cameras ---
# Camera index 0 = CSI port 0, index 1 = CSI port 1
# Swap these if the labels appear on the wrong side
cam_standard = Picamera2(0)
cam_wide     = Picamera2(1)

config_std  = cam_standard.create_preview_configuration(
    main={"format": "RGB888", "size": RESOLUTION}
)
config_wide = cam_wide.create_preview_configuration(
    main={"format": "RGB888", "size": RESOLUTION}
)

cam_standard.configure(config_std)
cam_wide.configure(config_wide)

cam_standard.start()
cam_wide.start()

SCREENSHOT_DELAY = 5  # seconds

print(f"Both cameras started. Screenshot in {SCREENSHOT_DELAY}s. Press ESC to quit.")

start_time       = time.time()
screenshot_saved = False

while True:
    frame_std  = cam_standard.capture_array()
    frame_wide = cam_wide.capture_array()

    # Convert RGB -> BGR for OpenCV display
    #frame_std  = cv2.cvtColor(frame_std,  cv2.COLOR_RGB2BGR)
    #frame_wide = cv2.cvtColor(frame_wide, cv2.COLOR_RGB2BGR)

    # --- Labels ---
    font       = cv2.FONT_HERSHEY_SIMPLEX
    label_args = (font, 0.9, (255, 255, 255), 2)

    cv2.putText(frame_wide,  "Standard (75 deg FOV)", (10, 35), *label_args)
    cv2.putText(frame_std, "Wide     (120 deg FOV)", (10, 35), *label_args)

    # Draw a coloured border so they're easy to tell apart
    cv2.rectangle(frame_std,  (0, 0), (RESOLUTION[0]-1, RESOLUTION[1]-1), (0, 0,   255), 4)  # red
    cv2.rectangle(frame_wide, (0, 0), (RESOLUTION[0]-1, RESOLUTION[1]-1), (0, 255,   0), 4)  # green

    # Combine side by side with a thin divider
    divider    = np.zeros((RESOLUTION[1], 6, 3), dtype=np.uint8)
    combined   = np.hstack([frame_std, divider, frame_wide])

    # --- Countdown / saved label ---
    elapsed   = time.time() - start_time
    remaining = SCREENSHOT_DELAY - elapsed

    if not screenshot_saved:
        cv2.putText(combined, f"Screenshot in {remaining:.1f}s", (10, RESOLUTION[1] - 15),
                    font, 0.8, (0, 255, 255), 2)

    # --- Auto-save ---
    if not screenshot_saved and elapsed >= SCREENSHOT_DELAY:
        cv2.imwrite("fov_comparison.png", combined)
        screenshot_saved = True
        print("Screenshot saved as 'fov_comparison.png'")

    if screenshot_saved:
        cv2.putText(combined, "Saved: fov_comparison.png", (10, RESOLUTION[1] - 15),
                    font, 0.8, (0, 255, 0), 2)

    cv2.imshow("FOV Comparison  |  Standard (left)  vs  Wide (right)", combined)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cam_standard.stop()
cam_wide.stop()
cv2.destroyAllWindows()
print("Done.")
