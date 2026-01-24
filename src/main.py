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

import inspect


def safe_call(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def main():
    print("[USING CONTROLLER FILE]", inspect.getfile(TelloController))
    print("[USING CONTROLLER SRC HEAD]", inspect.getsource(TelloController)[:200])

    kb = KeyboardState()
    controller = TelloController(kb)
    detector = ArUcoDetector()
    ui = DroneUI(panel_width=260, bottom_margin=60)

    # ArUco params
    try:
        aruco_params = aruco.DetectorParameters()
    except AttributeError:
        aruco_params = aruco.DetectorParameters_create()

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

    threading.Thread(target=controller.connect_and_start_stream, daemon=True).start()

    print("Controls: t=takeoff, g=land, p=approach ON/OFF, z=quit")

    prev_height = None
    total_alt = 0.0
    aruno_id = None
    aruno_last = None

    pos_xy = np.array([-1.8, 0.5], dtype=float)
    vel_xy = np.array([0.0, 0.0], dtype=float)
    POS_RANGE_X = 17.5
    POS_RANGE_Y = 10.0
    prev_time = time.perf_counter()
    ACCEL_DEADZONE = 0.09

    dm = DisplayManager(
        window_name="Tello UI",
        init_w=1600,
        init_h=900,
        fullscreen=True,
        ui_ratio=0.22,
        ui_min=260,
        ui_max=700,
    )

    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame_count = 0

    while True:
        marker_info = None

        frame_count += 1
        now = time.perf_counter()
        dt = max(1e-3, now - prev_time)
        prev_time = now

        DISPLAY_W, DISPLAY_H, UI_W = dm.update()

        left_w = max(1, DISPLAY_W - UI_W)
        if blank_frame.shape[0] != DISPLAY_H or blank_frame.shape[1] != left_w:
            blank_frame = np.zeros((DISPLAY_H, left_w, 3), dtype=np.uint8)

        connected = getattr(controller, "frame_read", None) is not None

        frame = None
        if connected:
            frame = safe_call(controller.get_frame, None)
        if frame is None or frame.size == 0:
            frame = blank_frame.copy()

        # ---- ArUco detect ----
        ids = None
        corners = None
        marker_info = None

        try:
            frame = np.ascontiguousarray(frame)

            def _run_detect(src):
                try:
                    return aruco.detectMarkers(src, aruco_dict, parameters=aruco_params)
                except AttributeError:
                    if hasattr(aruco, "ArucoDetector"):
                        ad = aruco.ArucoDetector(aruco_dict, aruco_params)
                        return ad.detectMarkers(src)
                    return (None, None, None)

            c, i, _ = _run_detect(frame)
            if i is None or len(i) == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                c, i, _ = _run_detect(gray)

            corners, ids = c, i

            if ids is not None and len(ids) > 0:
                aruco.drawDetectedMarkers(frame, corners, ids)
                aruno_id = int(ids.flatten()[0])
                aruno_last = aruno_id
            else:
                aruno_id = None

            marker_info = detector.get_marker_info(
                ids, corners, target_id=getattr(controller, "target_aruco_id", None)
            )

            # ★目視デバッグ：マーカー中心に点＋誤差線
            if marker_info is not None:
                cx, cy = marker_info["center"]
                cv2.circle(frame, (int(cx), int(cy)), 6, (0, 255, 255), -1, cv2.LINE_AA)  # 黄色点
                midx = frame.shape[1] // 2
                cv2.line(frame, (midx, int(cy)), (int(cx), int(cy)), (0, 255, 255), 2, cv2.LINE_AA)

        except Exception as e:
            if frame_count % 60 == 0:
                print(f"[WARN] ArUco detect failed: {e}")

        # ---- telemetry ----
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

            # 加速度積分（UI用）
            if agx is not None and agy is not None:
                try:
                    ax_body = float(agx) * 0.01
                    ay_body = float(agy) * 0.01
                    yaw_rad = np.deg2rad(float(yaw)) if yaw is not None else 0.0
                    c = np.cos(yaw_rad)
                    s = np.sin(yaw_rad)
                    ax = (c * ay_body) - (s * ax_body)
                    ay = -((s * ay_body) + (c * ax_body))

                    if abs(ax) < ACCEL_DEADZONE and abs(ay) < ACCEL_DEADZONE:
                        vel_xy[:] = 0.0
                    else:
                        vel_xy[0] += ax * dt
                        vel_xy[1] += ay * dt
                        vel_xy *= 0.985
                    pos_xy += vel_xy * dt
                    pos_xy[0] = np.clip(pos_xy[0], -POS_RANGE_X, POS_RANGE_X)
                    pos_xy[1] = np.clip(pos_xy[1], -POS_RANGE_Y, POS_RANGE_Y)
                except Exception:
                    pass

        # ---- UI ----
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

            # ★セミオート状態（UIに出す）
            approach_enabled=controller.approach_enabled,
            approach_state=getattr(controller, "approach_state", None),
            approach_vx=getattr(controller, "approach_vx", None),
            approach_yaw=getattr(controller, "approach_yaw", None),
            approach_err_x=getattr(controller, "approach_err_x", None),
            approach_size_px=getattr(controller, "approach_size_px", None),
        )

        out = dm.fit(out)
        cv2.imshow(dm.window_name, out)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("z"):
            break

        if connected:
            should_quit = controller.handle_key(key)
            if should_quit:
                break

        # ---- RC control ----
        if controller.in_flight:
            # 1) 手動入力反映
            controller.update_motion_from_keyboard()

            # 2) セミオートがONなら上書き（manual_active() 内で手動なら無効化）
            if getattr(controller, "approach_enabled", False):
                controller.update_approach_from_aruco(marker_info, frame.shape)

            # 3) 送信（毎フレーム）
            controller.update_motion()

        time.sleep(0.02)

    controller.cleanup()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
