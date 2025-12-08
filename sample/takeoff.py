#takeoff.py
import time
import cv2
from djitellopy import Tello

tello = Tello()
tello.connect()

tello.takeoff()

time.sleep(5)
tello.land()
