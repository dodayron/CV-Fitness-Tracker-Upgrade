#sound manager 
#prob dont really need but ill include it for better structure

import pygame
import time

# Initialize audio engine
pygame.mixer.init()

# Load audio to memory as a Sound
chimes = pygame.mixer.Sound("wind-chimes-2014.wav") 
rep_beep = pygame.mixer.Sound("success-alert-2039.wav")

start_sound = pygame.mixer.Sound("startup-sound-variation-5 p10.mp3")
start_sound.set_volume(1.0)  # max pygame volume

squat_instruct = pygame.mixer.Sound("squat instructions p10.wav")
squat_instruct.set_volume(1.0)  # max pygame volume
rCurl_instruct = pygame.mixer.Sound("Right curl instructions p10.wav")
rCurl_instruct.set_volume(1.0)  # max pygame volume
lCurl_instruct = pygame.mixer.Sound("Left curl instructions p10.wav")
lCurl_instruct.set_volume(1.0)  # max pygame volume
rLat_instruct = pygame.mixer.Sound("Right Lateral Raise instructions p10.wav")
rLat_instruct.set_volume(1.0)  # max pygame volume

def sound_quit():
    #Safely shuts down the audio engine
    pygame.mixer.quit()
