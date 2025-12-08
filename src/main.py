# main.py
import cv2

from tello_controller import TelloController
from aruco_detector import ArUcoDetector
from ui_overlay import DroneUI


def main():
    # 各コンポーネントを準備
    controller = TelloController()
    detector = ArUcoDetector()          # process(frame, draw=True, draw_id=True/False)
    ui = DroneUI(panel_width=260, bottom_margin=60)

    # Tello に接続して映像ストリーム開始
    controller.connect_and_start_stream()

    print(
        "Controls: "
        "t=takeoff, g=land, "
        "w/a/s/d=move, r/f=up/down, "
        "e/x=yaw, z=quit"
    )

    # 高度の変化量を積分する用
    prev_height = None          # 1つ前の高さ
    total_alt = 0.0             # 上下移動距離の累積（cm）

    while True:
        # ===== Tello からフレーム取得（左上に表示する映像） =====
        frame = controller.get_frame()   # 640x480 など想定

        # ===== ArUco 検出（映像上には枠だけ描画、ID文字は出さない） =====
        # aruco_detector.py 側の process に draw_id 引数を用意しておく:
        # def process(self, frame, draw=True, draw_id=True):
        frame, ids, corners = detector.process(frame, draw=True, draw_id=False)

        # ===== センサーデータ取得（失敗したら None のまま） =====
        # 角度 (roll, pitch, yaw)
        try:
            yaw = controller.tello.get_yaw()
        except Exception:
            yaw = None

        try:
            pitch = controller.tello.get_pitch()
        except Exception:
            pitch = None

        try:
            roll = controller.tello.get_roll()
        except Exception:
            roll = None

        # 高度（cm）
        try:
            height = controller.tello.get_height()
        except Exception:
            height = None

        # 高度の変化量を積分（絶対値で上下の距離を合計）
        if height is not None:
            if prev_height is not None:
                delta_h = abs(height - prev_height)
                total_alt += delta_h
            prev_height = height

        # バッテリー（%）
        try:
            battery = controller.tello.get_battery()
        except Exception:
            battery = None

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
        # ui_overlay.py 側で None のときは「NO DATA」表示してくれる

        # ===== 画面表示 =====
        cv2.imshow("Tello UI", canvas)

        # ===== キー入力処理（z で終了、他は TelloController に任せる） =====
        key = cv2.waitKey(1) & 0xFF
        if controller.handle_key(key):
            break

    # ===== 終了処理 =====
    controller.cleanup()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
