# tello_controller.py
import cv2
import numpy as np
from djitellopy import Tello
from keyboard_state import KeyboardState  # ★追加


class TelloController:
    """Telloの接続・映像取得・キー操作をまとめるクラス"""

    def __init__(self, keyboard_state: KeyboardState):
        self.tello = Tello()
        self.in_flight = False
        self.frame_read = None

        # キーボード状態
        self.kb = keyboard_state

        # 速度状態
        self.vx = 0
        self.vy = 0
        self.vz = 0
        self.yaw = 0

        self.speed = 40

        # 速度の大きさ（-100〜100）
        self.speed = 40

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
        cv2.waitKey() から渡されたキーを処理（終了・離着陸など）
        ※移動は update_motion_from_keyboard() 側でやる
        """

        # 終了（zで終了）
        if key == ord('z'):
            print("Exiting loop")
            return True

        # 離陸
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

        # 着陸
        elif key == ord('g'):
            print("Land requested")
            try:
                self.tello.land()
            except Exception as e:
                print(f"Land failed: {e}")
            self.in_flight = False
            self.vx = self.vy = self.vz = self.yaw = 0

        return False

    def update_motion_from_keyboard(self):
        """KeyboardState の状態から vx,vy,vz,yaw を更新"""
        if not self.in_flight:
            return

        vx = vy = vz = yaw = 0

        # 前後
        if self.kb.is_pressed('w'):
            vx += self.speed
        if self.kb.is_pressed('s'):
            vx -= self.speed

        # 左右
        if self.kb.is_pressed('d'):
            vy += self.speed
        if self.kb.is_pressed('a'):
            vy -= self.speed

        # 上下
        if self.kb.is_pressed('r'):
            vz += self.speed
        if self.kb.is_pressed('f'):
            vz -= self.speed

        # 回転
        if self.kb.is_pressed('e'):
            yaw += self.speed
        if self.kb.is_pressed('x'):
            yaw -= self.speed

        # スペースで即停止
        if self.kb.is_pressed(' '):
            vx = vy = vz = yaw = 0

        # 計算結果を反映
        self.vx, self.vy, self.vz, self.yaw = vx, vy, vz, yaw

    def update_motion(self):
        """send_rc_control を実行（毎フレーム呼ぶ）"""
        if not self.in_flight:
            return

        try:
            self.tello.send_rc_control(self.vx, self.vy, self.vz, self.yaw)
        except Exception as e:
            print(f"send_rc_control failed: {e}")
            
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
