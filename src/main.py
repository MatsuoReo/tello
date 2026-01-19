# main.py
import time
import cv2
import numpy as np
import threading
from cv2 import aruco


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

    # ArUco用（簡易パイプラインで使い回し）
    try:
        aruco_params = aruco.DetectorParameters()
    except AttributeError:
        aruco_params = aruco.DetectorParameters_create()
    # 小さいマーカー向けに少し緩め＋コーナー精錬
    aruco_params.adaptiveThreshWinSizeMin = 3
    aruco_params.adaptiveThreshWinSizeMax = 53
    aruco_params.adaptiveThreshWinSizeStep = 4
    aruco_params.minMarkerPerimeterRate = 0.02
    aruco_params.maxMarkerPerimeterRate = 5.0
    try:
        aruco_params.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX
    except Exception:
        pass
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

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
    aruno_id = None
    aruno_last = None
    # 簡易位置推定（加速度積分）
    # 画面上でやや左寄りに初期位置を置く（X<0で左）
    pos_xy = np.array([-1.8, 0.5], dtype=float)
    vel_xy = np.array([0.0, 0.0], dtype=float)
    POS_RANGE_X = 7.5  # UI上の表示範囲（左右, +-m相当）: 幅15m
    POS_RANGE_Y = 15.0  # UI上の表示範囲（上下, +-m相当）: 高さ30m
    prev_time = time.perf_counter()
    ACCEL_DEADZONE = 0.05  # m/s^2 未満は停止扱い

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
    using_webcam = False

    while True:
        frame_count += 1
        now = time.perf_counter()
        dt = max(1e-3, now - prev_time)
        prev_time = now

        # ===== 実ウィンドウサイズに追従 =====
        DISPLAY_W, DISPLAY_H, UI_W = dm.update()

        # 未接続時のブランクも「左映像分」サイズに寄せる
        left_w = max(1, DISPLAY_W - UI_W)
        if blank_frame.shape[0] != DISPLAY_H or blank_frame.shape[1] != left_w:
            blank_frame = np.zeros((DISPLAY_H, left_w, 3), dtype=np.uint8)

        # ===== 接続できているかの簡易判定 =====
        connected = getattr(controller, "frame_read", None) is not None
        using_webcam = False

        # ===== Tello からフレーム取得 =====
        frame = None
        if connected:
            frame = safe_call(controller.get_frame, None)

        # ===== Tello未接続時はブランク表示のみ =====
        if frame is None or frame.size == 0:
            using_webcam = False
            frame = blank_frame.copy()

        # ===== ArUco 検出 =====
        try:
            ids = None
            corners = None

            # OpenCV が扱いやすいよう連続化
            frame = np.ascontiguousarray(frame)

            def detect_simple(img):
                """
                tello_aruco と同等のシンプル検出（BGR → GRAY）。
                """
                def _run_detect(src):
                    try:
                        return aruco.detectMarkers(src, aruco_dict, parameters=aruco_params)
                    except AttributeError:
                        if hasattr(aruco, "ArucoDetector"):
                            try:
                                ad = aruco.ArucoDetector(aruco_dict, aruco_params)
                                return ad.detectMarkers(src)
                            except Exception:
                                pass
                        return (None, None, None)

                c, i, _ = _run_detect(img)
                if i is not None and len(i) > 0:
                    return c, i

                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                c, i, _ = _run_detect(gray)
                if i is not None and len(i) > 0:
                    return c, i
                return None, None

            corners, ids = detect_simple(frame)

            if ids is not None and len(ids) > 0:
                try:
                    aruco.drawDetectedMarkers(frame, corners, ids)
                except Exception:
                    frame = np.ascontiguousarray(frame)
                    aruco.drawDetectedMarkers(frame, corners, ids)
                try:
                    aruno_id = int(ids.flatten()[0])
                    aruno_last = aruno_id
                except Exception:
                    aruno_id = None
            else:
                aruno_id = None

            if frame_count % 30 == 0:
                label = "webcam" if using_webcam else "tello"
                print(f"[DEBUG {label}] ArUco ids: {ids.flatten().tolist() if ids is not None else None}")
                if aruno_last is not None:
                    print(f"[INFO] last detected id: {aruno_last}")
        except Exception as e:
            if frame_count % 60 == 0:
                print(f"[WARN] ArUco detect failed: {e}")


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
            if yaw is not None:
                try:
                    yaw = -float(yaw)
                except Exception:
                    pass
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

            # 加速度から位置を簡易積分（XYのみ）
            if agx is not None and agy is not None:
                try:
                    # agx: 前後, agy: 左右（機体座標）を想定してヨーで回転
                    ax_body = float(agx) * 0.01  # cm/s^2 -> m/s^2 相当
                    ay_body = float(agy) * 0.01
                    try:
                        yaw_rad = np.deg2rad(float(yaw)) if yaw is not None else 0.0
                    except Exception:
                        yaw_rad = 0.0
                    c = np.cos(yaw_rad)
                    s = np.sin(yaw_rad)
                    ax = (c * ay_body) - (s * ax_body)  # world X（左右）
                    ay = -((s * ay_body) + (c * ax_body))  # world Y（前後, 正方向を反転）

                    if abs(ax) < ACCEL_DEADZONE and abs(ay) < ACCEL_DEADZONE:
                        vel_xy[:] = 0.0
                    else:
                        vel_xy[0] += ax * dt
                        vel_xy[1] += ay * dt
                        vel_xy *= 0.985  # 簡易減衰でドリフト抑制
                    pos_xy += vel_xy * dt
                    pos_xy[0] = np.clip(pos_xy[0], -POS_RANGE_X, POS_RANGE_X)
                    pos_xy[1] = np.clip(pos_xy[1], -POS_RANGE_Y, POS_RANGE_Y)
                except Exception:
                    pass

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
            aruno=aruno_id,
            aruno_last=aruno_last,
            temp=temp,
            flight_time=flight_time,
            pos_xy=pos_xy,
            pos_range=(POS_RANGE_X, POS_RANGE_Y),
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

        if controller.in_flight:
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
