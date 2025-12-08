import time
import cv2
import numpy as np
from djitellopy import Tello
from cv2 import aruco  # ← 追加

# ArUco 用の辞書とパラメータを準備
ARUCO_DICT = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
ARUCO_PARAMS = aruco.DetectorParameters()

MOVE_DIST = 30   # 移動量（cm）
ROTATE_DEG = 30  # 回転角（度）


def main():
    tello = Tello()
    tello.connect()
    print(f"Battery: {tello.get_battery()}%")

    # 映像ストリーム開始
    try:
        tello.streamon()
        frame_read = tello.get_frame_read()
    except Exception:
        frame_read = None

    print("Controls: t=takeoff, g=land, w/a/s/d move, r/f up/down, e/x yaw right/left, z=quit")

    in_flight = False

    while True:
        # ====== フレーム取得 ======
        if frame_read is not None:
            frame = frame_read.frame
            if frame is None:
                frame = 255 * np.ones((480, 640, 3), dtype=np.uint8)
        else:
            frame = 255 * np.ones((480, 640, 3), dtype=np.uint8)

        # 必要ならサイズ調整
        frame = cv2.resize(frame, (640, 480))

        # ====== ArUco 検出部分 ======
        # グレースケールに変換（検出精度が上がる）
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # マーカー検出
        corners, ids, rejected = aruco.detectMarkers(
            gray,
            ARUCO_DICT,
            parameters=ARUCO_PARAMS
        )

        if ids is not None and len(ids) > 0:
            # マーカー枠とIDを描画（frame に上書き）
            aruco.drawDetectedMarkers(frame, corners, ids)

            # 検出IDをコンソールに表示
            print("Detected IDs:", ids.flatten())

            # 画面上にも先頭のIDを表示してみる
            text = f"ID: {int(ids[0])}"
            cv2.putText(frame, text, (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        # ====== 画像表示 ======
        cv2.imshow("Tello ArUco", frame)

        # ====== キー入力 ======
        key = cv2.waitKey(1) & 0xFF
        if key == ord('z'):
            print("Exiting loop")
            break
        elif key == ord('t'):
            print("Takeoff requested")
            try:
                battery = tello.get_battery()
                print(f"Battery before takeoff check: {battery}%")
                if battery < 20:
                    print("Battery too low for takeoff (requires >=20%). Charge battery and retry.")
                else:
                    tello.takeoff()
                    in_flight = True
            except Exception as e:
                print(f"Takeoff failed: {e}")
        elif key == ord('g'):
            print("Land requested")
            try:
                tello.land()
            except Exception as e:
                print(f"Land failed: {e}")
            in_flight = False
        elif key == ord('w'):
            print("Forward")
            tello.move_forward(MOVE_DIST)
        elif key == ord('s'):
            print("Backward")
            tello.move_back(MOVE_DIST)
        elif key == ord('a'):
            print("Left")
            tello.move_left(MOVE_DIST)
        elif key == ord('d'):
            print("Right")
            tello.move_right(MOVE_DIST)
        elif key == ord('r'):
            print("Up")
            tello.move_up(MOVE_DIST)
        elif key == ord('f'):
            print("Down")
            tello.move_down(MOVE_DIST)
        elif key == ord('e'):
            print("Yaw right")
            tello.rotate_clockwise(ROTATE_DEG)
        elif key == ord('x'):
            print("Yaw left")
            tello.rotate_counter_clockwise(ROTATE_DEG)

    # ====== 終了処理 ======
    try:
        tello.streamoff()
    except Exception:
        pass
    cv2.destroyAllWindows()

    if in_flight:
        try:
            print("Attempting emergency land before exit")
            tello.land()
        except Exception as e:
            print(f"Emergency land failed: {e}")

    tello.end()


if __name__ == "__main__":
    main()
