# tello_controller.py
import cv2
import numpy as np
from djitellopy import Tello


class TelloController:
    """Telloの接続・映像取得・キー操作をまとめるクラス"""

    def __init__(self, move_dist=30, rotate_deg=30):
        self.tello = Tello()
        self.move_dist = move_dist
        self.rotate_deg = rotate_deg
        self.in_flight = False
        self.frame_read = None

    def connect_and_start_stream(self):
        """Telloに接続して映像ストリーム開始"""
        self.tello.connect()
        print(f"Battery: {self.tello.get_battery()}%")
        self.tello.streamon()
        self.frame_read = self.tello.get_frame_read()

    def get_frame(self, size=(640, 480)):
        """現在のフレームを取得してリサイズして返す"""
        if self.frame_read is None:
            return 255 * np.ones((size[1], size[0], 3), dtype=np.uint8)

        frame = self.frame_read.frame
        if frame is None:
            return 255 * np.ones((size[1], size[0], 3), dtype=np.uint8)

        return cv2.resize(frame, size)

    def handle_key(self, key):
        """
        キー入力に応じてTelloを操作する。
        戻り値: True を返したらメインループ終了。
        """
        if key == ord('z'):
            print("Exiting loop")
            return True

        elif key == ord('t'):
            print("Takeoff requested")
            try:
                battery = self.tello.get_battery()
                print(f"Battery before takeoff check: {battery}%")
                if battery < 20:
                    print("Battery too low for takeoff (requires >=20%). Charge battery and retry.")
                else:
                    self.tello.takeoff()
                    self.in_flight = True
            except Exception as e:
                print(f"Takeoff failed: {e}")

        elif key == ord('g'):
            print("Land requested")
            try:
                self.tello.land()
            except Exception as e:
                print(f"Land failed: {e}")
            self.in_flight = False

        elif key == ord('w'):
            print("Forward")
            self.tello.move_forward(self.move_dist)

        elif key == ord('s'):
            print("Backward")
            self.tello.move_back(self.move_dist)

        elif key == ord('a'):
            print("Left")
            self.tello.move_left(self.move_dist)

        elif key == ord('d'):
            print("Right")
            self.tello.move_right(self.move_dist)

        elif key == ord('r'):
            print("Up")
            self.tello.move_up(self.move_dist)

        elif key == ord('f'):
            print("Down")
            self.tello.move_down(self.move_dist)

        elif key == ord('e'):
            print("Yaw right")
            self.tello.rotate_clockwise(self.rotate_deg)

        elif key == ord('x'):
            print("Yaw left")
            self.tello.rotate_counter_clockwise(self.rotate_deg)

        return False  # まだ終わらない

    def cleanup(self):
        """ストリーム停止・緊急着陸などの後片付け"""
        try:
            self.tello.streamoff()
        except Exception:
            pass

        if self.in_flight:
            try:
                print("Attempting emergency land before exit")
                self.tello.land()
            except Exception as e:
                print(f"Emergency land failed: {e}")

        self.tello.end()
