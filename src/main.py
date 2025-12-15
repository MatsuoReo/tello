# main.py
import time
import cv2
import numpy as np
import threading

from tello_controller import TelloController
from aruco_detector import ArUcoDetector
from ui_overlay import DroneUI
from keyboard_state import KeyboardState

from ui_components.display_manager import DisplayManager


def safe_call(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def main():
    kb = KeyboardState()

    # 各コンポーネントを準備
    controller = TelloController(kb)
    detector = ArUcoDetector()
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
    prev_height = None
    total_alt = 0.0

    # ===== 表示管理（ウィンドウ実サイズ追従 + 余白黒埋め + UI幅自動）=====
    dm = DisplayManager(
        window_name="Tello UI",
        init_w=1600,
        init_h=900,
        fullscreen=True,
        ui_ratio=0.22,
        ui_min=260,
        ui_max=700,
    )

    # Tello未接続でも表示できるダミーフレーム
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    frame_count = 0

    while True:
        frame_count += 1

        # ===== 実ウィンドウサイズに追従 =====
        DISPLAY_W, DISPLAY_H, UI_W = dm.update()

        # 未接続時のブランクも「左映像分」サイズに寄せる
        left_w = max(1, DISPLAY_W - UI_W)
        if blank_frame.shape[0] != DISPLAY_H or blank_frame.shape[1] != left_w:
            blank_frame = np.zeros((DISPLAY_H, left_w, 3), dtype=np.uint8)

        # ===== 接続できているかの簡易判定 =====
        connected = getattr(controller, "tello", None) is not None

        # ===== Tello からフレーム取得 =====
        frame = None
        if connected:
            frame = safe_call(controller.get_frame, None)

        if frame is None:
            frame = blank_frame.copy()

        # ===== ArUco 検出（軽量化：2フレームに1回）=====
        try:
            if frame_count % 2 == 0:
                frame, ids, corners = detector.process(frame, draw=True, draw_id=False)
        except Exception:
            pass

        # ===== センサーデータ =====
        yaw = pitch = roll = None
        height = None
        battery = None
        speed = None
        agx = agy = agz = None
        temp = None
        flight_time = None

        if connected:
            t = controller.tello

            yaw = safe_call(t.get_yaw, None)
            pitch = safe_call(t.get_pitch, None)
            roll = safe_call(t.get_roll, None)

            height = safe_call(t.get_height, None)
            battery = safe_call(t.get_battery, None)

            if height is not None:
                if prev_height is not None:
                    try:
                        total_alt += abs(float(height) - float(prev_height))
                    except Exception:
                        pass
                prev_height = height

            st = safe_call(t.get_current_state, {})

            try:
                agx = int(float(st.get("agx", 0)))
                agy = int(float(st.get("agy", 0)))
                agz = int(float(st.get("agz", 0)))
            except Exception:
                agx = agy = agz = None

            try:
                templ = float(st.get("templ", 0))
                temph = float(st.get("temph", 0))
                temp = (templ + temph) / 2.0
            except Exception:
                temp = None

            try:
                flight_time = int(float(st.get("time", 0)))
            except Exception:
                flight_time = None

            try:
                vgx = float(st.get("vgx", 0))
                vgy = float(st.get("vgy", 0))
                vgz = float(st.get("vgz", 0))
                speed = (vgx * vgx + vgy * vgy + vgz * vgz) ** 0.5
            except Exception:
                speed = None

        # ===== UI合成（右側パネル方式にするなら compose_side を使う）=====
        # ui_overlay がすでに ui_components/drone_ui を使っている前提なら compose_side が生えてるはず
        out = ui.compose_side(
            frame,
            display_w=DISPLAY_W,
            display_h=DISPLAY_H,
            ui_w=UI_W,
            ui_bg=(0, 0, 0),
            battery=battery,
            roll=roll,
            pitch=pitch,
            yaw=yaw,
            height=height,
            total_alt=total_alt,
            speed=speed,
            agx=agx, agy=agy, agz=agz,
            temp=temp,
            flight_time=flight_time,
        )

        # ===== “ちょい余白”対策：ウィンドウ実サイズに黒埋めで完全一致 =====
        out = dm.fit(out)

        cv2.imshow(dm.window_name, out)

        # ===== キー入力処理 =====
        key = cv2.waitKey(1) & 0xFF
        if key == ord("z"):
            break

        if connected:
            try:
                if controller.handle_key(key):
                    break
            except Exception:
                pass

            try:
                controller.update_motion_from_keyboard()
                controller.update_motion()
            except Exception:
                pass

        time.sleep(0.03)

    try:
        controller.cleanup()
    except Exception:
        pass
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
