import time
import cv2
import numpy as np
from djitellopy import Tello

def main():
    tello = Tello()
    tello.connect()
    print(f"Battery: {tello.get_battery()}%")

    # カメラ映像
    try:
        tello.streamon()
        frame_read = tello.get_frame_read()
    except Exception:
        frame_read = None

    print("Controls:")
    print("  t: takeoff, g: land, z: quit")
    print("  w/s: 前後, a/d: 左右, r/f: 上下, e/x: 回転, space: 全停止")

    in_flight = False

    # ここがポイント：速度の状態を保持する変数
    vx, vy, vz, yaw = 0, 0, 0, 0   # -100〜100 の範囲で指定

    while True:
        # 映像表示
        if frame_read is not None:
            frame = frame_read.frame
            if frame is None:
                frame = 255 * np.ones((480, 640, 3), dtype=np.uint8)
        else:
            frame = 255 * np.ones((480, 640, 3), dtype=np.uint8)

        frame = cv2.resize(frame, (640, 480))
        cv2.imshow("tello", frame)

        key = cv2.waitKey(1) & 0xFF

        # --- キーの処理 ---

        if key == ord('z'):
            print("Exiting loop")
            break

        elif key == ord('t'):
            print("Takeoff requested")
            try:
                battery = tello.get_battery()
                print(f"Battery: {battery}%")
                if battery < 20:
                    print("Battery too low for takeoff (>=20% needed)")
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
            vx = vy = vz = yaw = 0  # 念のため停止

        # ここからが「リアルタイム操作」部分
        elif key == ord('w'):   # 前へ
            vx = 40
        elif key == ord('s'):   # 後ろへ
            vx = -40
        elif key == ord('a'):   # 左へ
            vy = -40
        elif key == ord('d'):   # 右へ
            vy = 40
        elif key == ord('r'):   # 上へ
            vz = 40
        elif key == ord('f'):   # 下へ
            vz = -40
        elif key == ord('e'):   # 右回転
            yaw = 40
        elif key == ord('x'):   # 左回転
            yaw = -40

        # スペースキーで完全停止
        elif key == ord(' '):
            vx = vy = vz = yaw = 0

        # --- 速度コマンドを送る ---
        try:
            if in_flight:
                tello.send_rc_control(vx, vy, vz, yaw)
        except Exception as e:
            print(f"send_rc_control failed: {e}")

        # 送信頻度を落とす（20Hzくらい）
        time.sleep(0.05)

    # 終了処理
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
