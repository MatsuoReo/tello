# main.py
import time
import cv2
from tello_controller import TelloController
from aruco_detector import ArUcoDetector
from keyboard_state import KeyboardState


def main():
    kb = KeyboardState()
    controller = TelloController(kb)
    detector = ArUcoDetector()

    controller.connect_and_start_stream()
    print("Controls: t=takeoff, g=land, w/a/s/d move, r/f up/down, e/x yaw right/left, z=quit")

    while True:
        # Telloからフレームを取得
        frame = controller.get_frame()

        # ArUco検出（frameに枠＆IDを描画）
        frame, ids, corners = detector.process(frame)

        # 画面に表示
        cv2.imshow("Tello ArUco", frame)

        # キー入力をTelloControllerに渡す
        key = cv2.waitKey(1) & 0xFF
        if controller.handle_key(key):
            break

        # ここで「今押されているキー」から速度を決める
        controller.update_motion_from_keyboard()
        controller.update_motion()

        # 送信頻度を落としすぎない程度のスリープ（だいたい20Hz）
        time.sleep(0.05)

    controller.cleanup()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
