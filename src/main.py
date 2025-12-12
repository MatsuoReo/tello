# main.py
import time
import cv2
import numpy as np
import threading

from tello_controller import TelloController
from aruco_detector import ArUcoDetector
from ui_overlay import DroneUI
from keyboard_state import KeyboardState


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

    # ウィンドウはループ外で1回だけ作る（毎フレーム作ると重い＆不安定）
    window_name = "Tello UI"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    try:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    except Exception:
        # 環境によっては効かないので無視
        pass

    # 画面サイズ（取得できたら、その解像度に合わせて「先にフレームを拡大 → UIを描画」する）
    target_w = None
    target_h = None

    # Tello未接続でも表示できるダミーフレーム（あとでターゲットサイズが分かったら作り直す）
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    while True:
        # ===== 接続できているかの簡易判定 =====
        connected = getattr(controller, "frame_read", None) is not None

        # ===== Tello からフレーム取得 =====
        frame = None
        if connected:
            frame = safe_call(controller.get_frame, None)

        if frame is None:
            frame = blank_frame.copy()

        # ===== フルスクリーンの実サイズを取得（取れたら以後それに合わせて描画） =====
        if target_w is None or target_h is None:
            try:
                x, y, w, h = cv2.getWindowImageRect(window_name)
                if w > 0 and h > 0:
                    target_w, target_h = int(w), int(h)
                    blank_frame = np.zeros((target_h, target_w, 3), dtype=np.uint8)
            except Exception:
                pass

        # ===== 先にフレームをターゲット解像度に合わせる =====
        if target_w is not None and target_h is not None:
            try:
                if frame.shape[1] != target_w or frame.shape[0] != target_h:
                    frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
            except Exception:
                pass

        # ===== ArUco 検出 =====
        try:
            frame, ids, corners = detector.process(frame, draw=True, draw_id=False)
        except Exception:
            pass

        # ===== センサーデータ（未接続時はダミー値） =====
        if not connected:
            yaw = 0
            pitch = 0
            roll = 0
            height = 0
            battery = 79

            # 追加：速度（UIのSPDに渡す）
            speed = 0
        else:
            t = controller.tello

            yaw = safe_call(t.get_yaw, 0)
            pitch = safe_call(t.get_pitch, 0)
            roll = safe_call(t.get_roll, 0)

            height = safe_call(t.get_height, 0)
            battery = safe_call(t.get_battery, 100)

            # 高度の変化量を積分（通信ありのときだけ更新）
            if height is not None:
                if prev_height is not None:
                    try:
                        total_alt += abs(float(height) - float(prev_height))
                    except Exception:
                        pass
                prev_height = height

            # 追加：速度
            # djitellopy だと get_speed_x/y/z があることが多い
            sx = safe_call(getattr(t, "get_speed_x"), None) if hasattr(t, "get_speed_x") else None
            sy = safe_call(getattr(t, "get_speed_y"), None) if hasattr(t, "get_speed_y") else None
            sz = safe_call(getattr(t, "get_speed_z"), None) if hasattr(t, "get_speed_z") else None

            if sx is not None and sy is not None and sz is not None:
                try:
                    speed = (float(sx) ** 2 + float(sy) ** 2 + float(sz) ** 2) ** 0.5
                except Exception:
                    speed = None
            else:
                # 取れない環境向け：NoneにしてUI側で "--" 表示にしてもOK
                speed = None

        # ===== UI描画 =====
        canvas = ui.draw(
            frame,
            battery=battery,
            roll=roll,
            pitch=pitch,
            yaw=yaw,
            height=height,
            total_alt=total_alt,
            speed=speed,   # ←追加
        )

        # ===== 画面表示 =====
        cv2.imshow(window_name, canvas)

        # ===== キー入力処理 =====
        key = cv2.waitKey(1) & 0xFF

        if key == ord("z"):
            break

        # 未接続のときは操作コマンドを送らない（固まり/タイムアウト対策）
        if connected:
            try:
                if controller.handle_key(key):
                    break
            except Exception:
                pass

            # ここで「今押されているキー」から速度を決める
            try:
                controller.update_motion_from_keyboard()
                controller.update_motion()
            except Exception:
                pass

        time.sleep(0.05)

    try:
        controller.cleanup()
    except Exception:
        pass
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
