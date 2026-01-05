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

        self.speed = 100
        self.brake_ratio = 0.6

        # ★オートランディング用：高さ→前進距離の比例係数 d = k * h
        #   cキーでキャリブレーションして中身を決める
        self.k_forward_per_height = None      # None の間はオートランディング不可
        self.calib_distance_cm = 420          # 基準高さで「この距離だけ前に進めばよい」(3m)

    # --------------------------------------------------------
    # 接続・映像
    # --------------------------------------------------------
    def connect_and_start_stream(self):
        """Telloに接続して映像ストリーム開始"""
        self.tello.connect()
        print(f"Battery: {self.tello.get_battery()}%")
        self.tello.streamon()
        self.frame_read = self.tello.get_frame_read()

    def get_frame(self):
        """現在のフレームをそのまま返す（リサイズは main 側でやる）"""
        if self.frame_read is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)

        frame = self.frame_read.frame
        if frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)

        # ★ 色変換も軽く：cv2.cvtColor ではなく numpy で RGB→BGR
        frame = frame[:, :, ::-1]

        return frame

    # --------------------------------------------------------
    # キー入力（単発系：終了・離着陸・オートランディング）
    # --------------------------------------------------------
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

        # 着陸（通常）
        elif key == ord('g'):
            print("Land requested")
            try:
                self.tello.land()
            except Exception as e:
                print(f"Land failed: {e}")
            self.in_flight = False
            self.vx = self.vy = self.vz = self.yaw = 0

        # ★ キャリブレーション（基準高さで3m進めば良いときの k を計算）
        elif key == ord('c'):
            self.calibrate_auto_landing()

        # ★ オートランディング（画面中央に見えている地点の上へ前進してから着陸）
        elif key == ord('l'):
            self.auto_land_to_center()

        return False

    # --------------------------------------------------------
    # オートランディング関連
    # --------------------------------------------------------
    def calibrate_auto_landing(self):
        """
        現在の高さ h0 と「基準距離 calib_distance_cm」から比例定数 k = d0 / h0 を求める。
        事前に「takeoff直後の高さで、画面中央の点の真上に来るまで3m進めば良い」
        という状況で c キーを押してキャリブする想定。
        """
        if not self.in_flight:
            print("[AUTO-LAND] Not in flight. Take off first.")
            return

        try:
            h0 = self.tello.get_height()  # cm
        except Exception as e:
            print(f"[AUTO-LAND] Failed to get height: {e}")
            return

        if h0 is None or h0 <= 0:
            print(f"[AUTO-LAND] Invalid height for calibration: {h0}")
            return

        k = self.calib_distance_cm / float(h0)
        self.k_forward_per_height = k
        print(f"[AUTO-LAND] Calibrated: height={h0}cm, dist={self.calib_distance_cm}cm → k={k:.3f}")

    def auto_land_to_center(self):
        """
        画面中央に見えている地点の上まで前進してから着陸する。
        d = k * h の関係を使う。
        """
        if not self.in_flight:
            print("[AUTO-LAND] Not in flight.")
            return

        if self.k_forward_per_height is None:
            print("[AUTO-LAND] Not calibrated yet. Press 'c' at the reference height first.")
            return

        # 現在の高さを取得
        try:
            h = self.tello.get_height()  # cm
        except Exception as e:
            print(f"[AUTO-LAND] Failed to get height: {e}")
            return

        if h is None or h <= 0:
            print(f"[AUTO-LAND] Invalid current height: {h}")
            return

        # 前進距離 d = k * h
        d = self.k_forward_per_height * float(h)

        # 安全のため距離を制限（例: 20〜500cm）
        d_clamped = int(max(20, min(d, 1000)))

        print(f"[AUTO-LAND] height={h}cm → move_forward ≈ {d:.1f}cm (clamped to {d_clamped}cm)")

        try:
            # まず前進
            self.tello.move_forward(d_clamped)
            # その後着陸
            self.tello.land()
            self.in_flight = False
            self.vx = self.vy = self.vz = self.yaw = 0
            print("[AUTO-LAND] Landed.")
        except Exception as e:
            print(f"[AUTO-LAND] Auto land failed: {e}")

    # --------------------------------------------------------
    # キーボードによるマニュアル操作（リアルタイム）
    # --------------------------------------------------------
    def update_motion_from_keyboard(self):
        if not self.in_flight:
            return

        vx = vy = vz = yaw = 0

        speed = self.speed
        if self.kb.is_pressed('shift'):
            speed = self.speed // 3  # 精密モード（100→33など）

        # 前後
        if self.kb.is_pressed('d'):
            vx += speed
        if self.kb.is_pressed('a'):
            vx -= speed

        # 左右
        if self.kb.is_pressed('w'):
            vy += speed
        if self.kb.is_pressed('s'):
            vy -= speed

        # 上下
        if self.kb.is_pressed('r'):
            vz += speed
        if self.kb.is_pressed('f'):
            vz -= speed

        # 回転
        if self.kb.is_pressed('e'):
            yaw += speed
        if self.kb.is_pressed('q'):
            yaw -= speed

        # スペースで即停止
        if self.kb.is_pressed('space'):
            vx = vy = vz = yaw = 0

        self.vx, self.vy, self.vz, self.yaw = vx, vy, vz, yaw

    def update_motion(self):
        """send_rc_control を実行（毎フレーム呼ぶ）"""
        if not self.in_flight:
            return

        try:
            self.tello.send_rc_control(self.vx, self.vy, self.vz, self.yaw)
        except Exception as e:
            print(f"send_rc_control failed: {e}")

    # --------------------------------------------------------
    # 後片付け
    # --------------------------------------------------------
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
