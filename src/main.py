# main.py
import time
import cv2
import numpy as np
import threading

from tello_controller import TelloController
from aruco_detector import ArUcoDetector
from ui_overlay import DroneUI
from keyboard_state import KeyboardState


def main():
    kb = KeyboardState()
    # 各コンポーネントを準備
    controller = TelloController(kb)
    detector = ArUcoDetector()          # process(frame, draw=True, draw_id=True/False)
    ui = DroneUI(panel_width=260, bottom_margin=60)

    # 先にUIを出したいので、接続は別スレッドで開始（ここで待たない）
    threading.Thread(target=controller.connect_and_start_stream, daemon=True).start()

    print(
        "Controls: "
        "t=takeoff, g=land, "
        "w/a/s/d=move, r/f=up/down, "
        "e/x=yaw, z=quit"
    )

    # 高度の変化量を積分する用
    prev_height = None          # 1つ前の高さ
    total_alt = 0.0             # 上下移動距離の累積（cm）

    # Tello未接続でも表示できるダミーフレーム
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    while True:
        # ===== 接続できているかの簡易判定 =====
        # connect_and_start_stream() が成功すると frame_read が設定される前提
        connected = getattr(controller, "frame_read", None) is not None

        # ===== Tello からフレーム取得（左上に表示する映像） =====
        frame = None
        if connected:
            try:
                frame = controller.get_frame()
            except Exception:
                frame = None

        if frame is None:
            frame = blank_frame.copy()

        # ===== ArUco 検出（映像上には枠だけ描画、ID文字は出さない） =====
        try:
            frame, ids, corners = detector.process(frame, draw=True, draw_id=False)
        except Exception:
            # 検出が失敗してもUIは落とさない
            pass

        # ===== センサーデータ（未接続時はダミー値） =====
        if not connected:
            # 通信がない時に表示したい適当な値
            yaw = 0
            pitch = 0
            roll = 0
            height = 0
            battery = 79
        else:
            yaw = pitch = roll = height = battery = None

            try:
                yaw = controller.tello.get_yaw()
            except Exception:
                yaw = 0

            try:
                pitch = controller.tello.get_pitch()
            except Exception:
                pitch = 0

            try:
                roll = controller.tello.get_roll()
            except Exception:
                roll = 0

            try:
                height = controller.tello.get_height()
            except Exception:
                height = 0

            # 高度の変化量を積分（通信ありのときだけ更新）
            if height is not None:
                if prev_height is not None:
                    total_alt += abs(height - prev_height)
                prev_height = height

            try:
                battery = controller.tello.get_battery()
            except Exception:
                battery = 100

        # ===== UI キャンバスを作成（黒背景＋右パネル＋下ヘルプ） =====
        canvas = ui.draw(
            frame,
            battery=battery,
            roll=roll,
            pitch=pitch,
            yaw=yaw,
            height=height,
            total_alt=total_alt,
        )

        # ===== 画面表示 =====
        cv2.imshow("Tello UI", canvas)

        # ===== キー入力処理 =====
        key = cv2.waitKey(1) & 0xFF

        # z は未接続でも終了できるようにする
        if key == ord("z"):
            break

        # 未接続のときは操作コマンドを送らない（固まり/タイムアウト対策）
        if connected:
            try:
                if controller.handle_key(key):
                    break
            except Exception:
                # ここで落とさない
                pass

        # ここで「今押されているキー」から速度を決める
        controller.update_motion_from_keyboard()
        controller.update_motion()

        # 送信頻度を落としすぎない程度のスリープ（だいたい20Hz）
        time.sleep(0.05)

    try:
        controller.cleanup()
    except Exception:
        pass
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
