# led_test.py - run this directly: sudo python led_test.py
import board
import neopixel
import time

# Test Strip 1
print("Testing Strip 1 (D18)...")
strip1 = neopixel.NeoPixel(board.D18, 8, brightness=0.5, auto_write=False, pixel_order=neopixel.GRB)
strip1.fill((255, 0, 0))  # all red
strip1.show()
time.sleep(2)
strip1.fill((0, 0, 0))
strip1.show()

# Test Strip 2
print("Testing Strip 2 (D21)...")
strip2 = neopixel.NeoPixel(board.D21, 8, brightness=0.5, auto_write=False, pixel_order=neopixel.GRB)
strip2.fill((255, 0, 0))  # all red
strip2.show()
time.sleep(2)
strip2.fill((0, 0, 0))
strip2.show()

print("Done.")
