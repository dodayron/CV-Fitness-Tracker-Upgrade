import board
import neopixel
import time

class LEDManager:
    def __init__(self, bar_pin=board.D18, rep_pin=board.D21, num_pixels=8):
        self.num_pixels = num_pixels

        # Strip 1 - Progress Bar (GPIO 18)
        self.bar_pixels = neopixel.NeoPixel(
            bar_pin, num_pixels, brightness=0.2, auto_write=False, pixel_order=neopixel.GRB
        )

        # Strip 2 - Rep Counter (GPIO 21)
        self.rep_pixels = neopixel.NeoPixel(
            rep_pin, num_pixels, brightness=0.2, auto_write=False, pixel_order=neopixel.GRB
        )

        self.last_bar_count = -1   # avoids redundant bar rewrites
        self.last_rep_count = -1   # avoids redundant rep rewrites

    # STRIP 1: Progress Bar
    def update_bar(self, percentage):
        led2light = int((percentage / 100) * self.num_pixels)
        led2light = max(0, min(led2light, self.num_pixels))

        if led2light == self.last_bar_count:
            return

        self.last_bar_count = led2light
        color = (0, 255, 0) if led2light == self.num_pixels else (0, 0, 255)

        for i in range(self.num_pixels):
            self.bar_pixels[i] = color if i < led2light else (0, 0, 0)

        self.bar_pixels.show()

    # STRIP 2: Rep Counter
    def update_reps(self, rep_count):
        display_count = rep_count % self.num_pixels # remainder of count / 8
        if display_count == self.last_rep_count:
            return

        self.last_rep_count = display_count

        if display_count == 0 and rep_count > 0: # full set complete
            self._rainbow_complete()  # celebrate!
            self.last_rep_count = 0  # reset counter
        else:
            for i in range(self.num_pixels):
                self.rep_pixels[i] = (0, 255, 0) if i < display_count else (0, 0, 0)
            self.rep_pixels.show()

    def _rainbow_complete(self):
        rainbow_colors = [
            (255, 0, 0),     # Red
            (255, 127, 0),   # Orange
            (255, 255, 0),   # Yellow
            (0, 255, 0),     # Green
            (0, 0, 255),     # Blue
            (75, 0, 130),    # Indigo
            (148, 0, 211),   # Violet
            (255, 20, 147),  # Pink
        ]
        for _ in range(2):  # flash 2 times
            for color in rainbow_colors:
                self.rep_pixels.fill(color)
                self.rep_pixels.show()
                time.sleep(0.05)
        self.clear()

    # --- Clear Both Strips ---
    def clear(self):
        self.bar_pixels.fill((0, 0, 0))
        self.bar_pixels.show()
        self.rep_pixels.fill((0, 0, 0))
        self.rep_pixels.show()
