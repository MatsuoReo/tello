# ui_overlay.py
import cv2
import numpy as np

TEXT_COLOR   = (230, 230, 230)   # 白っぽい
ACCENT_COLOR = (255, 100, 200)   # ピンク
CYAN         = (255, 255, 0)     # シアン


class DroneUI:
    """
    黒背景 + 左に映像, 右に情報パネル
    下に操作ヘルプを出すUI
    """

    def __init__(self, panel_width: int = 260, bottom_margin: int = 60):
        self.panel_width = panel_width
        self.bottom_margin = bottom_margin

    # ---------- 角度メーターを描く内部関数 ----------
    def _draw_gauge(self, img, center, radius, value, vmin, vmax, label):
        """
        半円ゲージ + 針 を描画する
        value が None のときは「NO DATA」を表示して針は描かない
        """
        # 外枠の半円（210°～ -30°くらいの上側アーチ）
        start_angle = 210
        end_angle   = -30
        cv2.ellipse(
            img, center, (radius, radius),
            0, start_angle, end_angle,
            CYAN, 2, cv2.LINE_AA
        )

        # 目盛り線
        for t in np.linspace(0.0, 1.0, 5):
            a = np.deg2rad(start_angle + (end_angle - start_angle) * t)
            x1 = int(center[0] + radius * 0.8 * np.cos(a))
            y1 = int(center[1] - radius * 0.8 * np.sin(a))
            x2 = int(center[0] + radius * 0.9 * np.cos(a))
            y2 = int(center[1] - radius * 0.9 * np.sin(a))
            cv2.line(img, (x1, y1), (x2, y2), (80, 80, 80), 1, cv2.LINE_AA)

        # ラベル
        cv2.putText(
            img, f"{label}",
            (center[0] - radius, center[1] + radius + 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, CYAN, 1, cv2.LINE_AA
        )

        if value is None:
            # 針は描かず「NO DATA」
            cv2.putText(
                img, "NO DATA",
                (center[0] - radius, center[1] + radius + 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (150, 150, 150), 1, cv2.LINE_AA
            )
            cv2.circle(img, center, 4, (100, 100, 100), -1, cv2.LINE_AA)
            return

        # 値を範囲内にクリップ
        value = max(min(value, vmax), vmin)

        # value -> 角度へマッピング
        t = (value - vmin) / (vmax - vmin)  # 0～1
        ang = start_angle + (end_angle - start_angle) * t
        ang_rad = np.deg2rad(ang)

        # 針
        x_needle = int(center[0] + radius * 0.75 * np.cos(ang_rad))
        y_needle = int(center[1] - radius * 0.75 * np.sin(ang_rad))
        cv2.line(
            img, center, (x_needle, y_needle),
            ACCENT_COLOR, 2, cv2.LINE_AA
        )

        # 中心点
        cv2.circle(img, center, 4, ACCENT_COLOR, -1, cv2.LINE_AA)

        # 数値表示
        cv2.putText(
            img, f"{int(value)} deg",
            (center[0] - radius, center[1] + radius + 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, TEXT_COLOR, 1, cv2.LINE_AA
        )

    # ---------- メイン描画 ----------
    def draw(
        self,
        frame,
        *,
        battery=None,
        roll=None,
        pitch=None,
        yaw=None,
        height=None,
        total_alt=None,
    ):
        """
        左に frame の映像、右にステータス、
        下に操作ヘルプを描画したキャンバスを返す。

        値が None の場合は「NO DATA」表示にする。
        """
        h, w, _ = frame.shape

        H = h + self.bottom_margin
        W = w + self.panel_width

        # 黒背景キャンバス
        canvas = np.zeros((H, W, 3), dtype=np.uint8)

        # 左上に映像を貼る
        canvas[0:h, 0:w] = frame

        # 映像とパネルの境界線
        cv2.line(canvas, (w, 0), (w, h), (80, 80, 80), 1, cv2.LINE_AA)

        # 右パネルの描画
        x0 = w + 20
        y  = 40

        # タイトル
        cv2.putText(
            canvas,
            "TELLO STATUS",
            (x0, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            ACCENT_COLOR,
            2,
            cv2.LINE_AA,
        )
        y += 40

        # バッテリー
        cv2.putText(
            canvas,
            "BATTERY",
            (x0, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            CYAN,
            1,
            cv2.LINE_AA,
        )
        y += 25

        if battery is None:
            cv2.putText(
                canvas,
                "NO DATA",
                (x0 + 10, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (150, 150, 150),
                1,
                cv2.LINE_AA,
            )
        else:
            cv2.putText(
                canvas,
                f"{battery:3d} %",
                (x0 + 10, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                TEXT_COLOR,
                2,
                cv2.LINE_AA,
            )
        y += 35

        # --- 角度ゲージ（3つ） ---
        gauge_center_x = x0 + 100
        base_y = y + 40
        radius = 40

        self._draw_gauge(canvas,
                         (gauge_center_x, base_y),
                         radius,
                         roll,   # Noneなら中でNO DATA
                         -90, 90,
                         "ROLL (X)")

        self._draw_gauge(canvas,
                         (gauge_center_x, base_y + 110),
                         radius,
                         pitch,
                         -90, 90,
                         "PITCH (Y)")

        self._draw_gauge(canvas,
                         (gauge_center_x, base_y + 220),
                         radius,
                         yaw,
                         -180, 180,
                         "YAW (Z)")

        # --- 高度と積分値 ---
        y_alt = base_y + 220 + radius + 60
        if y_alt < h - 20:
            cv2.putText(
                canvas,
                "ALTITUDE",
                (x0, y_alt),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                CYAN,
                1,
                cv2.LINE_AA,
            )
            y_alt += 25

            if (height is None) and (total_alt is None):
                cv2.putText(
                    canvas,
                    "NO DATA",
                    (x0 + 10, y_alt),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (150, 150, 150),
                    1,
                    cv2.LINE_AA,
                )
            else:
                if height is not None:
                    cv2.putText(
                        canvas,
                        f"current : {height:4d} cm",
                        (x0 + 10, y_alt),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        TEXT_COLOR,
                        2,
                        cv2.LINE_AA,
                    )
                    y_alt += 22

                if total_alt is not None:
                    cv2.putText(
                        canvas,
                        f"sum dH : {int(total_alt):4d} cm",
                        (x0 + 10, y_alt),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        TEXT_COLOR,
                        2,
                        cv2.LINE_AA,
                    )

        # === 下の余白に操作ヘルプ ===
        controls = "[T]takeoff  [G]land  [W/A/S/D]move  [R/F]up/down  [E/X]yaw  [Z]quit"
        cv2.putText(
            canvas,
            controls,
            (20, H - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (160, 160, 160),
            1,
            cv2.LINE_AA,
        )

        return canvas
