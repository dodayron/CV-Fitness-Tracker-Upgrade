import cv2
import time
from datetime import datetime

class ScreenshotManager:
    def __init__(self, interval=10):
        self.interval = interval
        self.last_time = time.time()

    def update(self, frame, key=None):
        # Timed screenshot
        if time.time() - self.last_time >= self.interval:
            self._save(frame, "timed")
            self.last_time = time.time()

        # Manual screenshot on 'p' key
        if key == ord('p'):
            self._save(frame, "manual")

    def _save(self, frame, source):
        filename = f"screenshot_{source}_{datetime.now().strftime('%H%M%S')}.png"
        cv2.imwrite(filename, frame)
        print(f"Saved: {filename}")
