# ui_overlay.py
import cv2
import numpy as np

TEXT = (245, 245, 245)
PANEL = (0, 0, 0)

# ネオン系（BGR）
CYAN = (255, 255, 120)
PURPLE = (255, 120, 220)
TICK = (160, 160, 160)

OUTLINE = (0, 0, 0)


class DroneUI:
    def __init__(self, panel_width: int = 260, bottom_margin: int = 60):
        self.panel_width = panel_width
        self.bottom_margin = bottom_margin

    def _blend_rect(self, img, x1, y1, x2, y2, alpha=0.28):
        x1 = max(0, min(img.shape[1] - 1, int(x1)))
        x2 = max(0, min(img.shape[1], int(x2)))
        y1 = max(0, min(img.shape[0] - 1, int(y1)))
        y2 = max(0, min(img.shape[0], int(y2)))
        if x2 <= x1 or y2 <= y1:
            return
        roi = img[y1:y2, x1:x2]
        overlay = roi.copy()
        overlay[:] = PANEL
        cv2.addWeighted(overlay, alpha, roi, 1 - alpha, 0, roi)

    def _put_outline(self, img, text, org, scale, color, thickness=1, outline=2):
        cv2.putText(img, str(text), org, cv2.FONT_HERSHEY_SIMPLEX, scale, OUTLINE, outline, cv2.LINE_AA)
        cv2.putText(img, str(text), org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

    def _put_right_outline(self, img, text, right_x, y, scale, color, thickness=1, outline=2):
        (tw, _), _ = cv2.getTextSize(str(text), cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        self._put_outline(img, text, (int(right_x - tw), int(y)), scale, color, thickness, outline)

    def _boxed_text(self, img, text, x, y, scale, color, pad=6, thickness=1, outline=2, alpha=0.18):
        (tw, th), _ = cv2.getTextSize(str(text), cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        self._blend_rect(img, x - pad, y - th - pad, x + tw + pad, y + pad, alpha=alpha)
        self._put_outline(img, text, (x, y), scale, color, thickness, outline)

    def _center_text(self, img, text, cx, y, scale, color, thickness=1, outline=2):
        (tw, _), _ = cv2.getTextSize(str(text), cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        x = int(cx - tw // 2)
        self._put_outline(img, text, (x, y), scale, color, thickness, outline)

    def _neon_gauge(self, img, center, r, value, vmin, vmax, label_text):
        """
        重なり防止のため：
        - 数値は「ゲージの下」ではなく「ゲージの中」に描く
        """
        cx, cy = center

        arc_thick = 1
        needle_thick = 1

        start_deg = 210
        end_deg = -30

        # 弧（細め）
        cv2.ellipse(img, (cx, cy), (r, r), 0, start_deg, end_deg, (110, 110, 60), arc_thick + 1, cv2.LINE_AA)
        cv2.ellipse(img, (cx, cy), (r, r), 0, start_deg, end_deg, CYAN, arc_thick, cv2.LINE_AA)

        # 目盛り
        for t in np.linspace(0.18, 0.82, 4):
            ang = np.deg2rad(start_deg + (end_deg - start_deg) * t)
            x1 = int(cx + (r * 0.74) * np.cos(ang))
            y1 = int(cy - (r * 0.74) * np.sin(ang))
            x2 = int(cx + (r * 0.86) * np.cos(ang))
            y2 = int(cy - (r * 0.86) * np.sin(ang))
            cv2.line(img, (x1, y1), (x2, y2), TICK, 1, cv2.LINE_AA)

        # 針
        if value is not None:
            try:
                v = float(value)
                v = max(vmin, min(vmax, v))
                t = (v - vmin) / (vmax - vmin) if vmax != vmin else 0.5
                deg = start_deg + (end_deg - start_deg) * t
                rad = np.deg2rad(deg)
                nx = int(cx + (r * 0.82) * np.cos(rad))
                ny = int(cy - (r * 0.82) * np.sin(rad))
                cv2.line(img, (cx, cy), (nx, ny), PURPLE, needle_thick, cv2.LINE_AA)
            except Exception:
                pass

        # 中心ドット
        cv2.circle(img, (cx, cy), 2, PURPLE, -1, cv2.LINE_AA)

        # 数値はゲージ内（ここが重なり解消の本体）
        if value is None:
            vtxt = "--"
        else:
            try:
                vtxt = str(int(round(float(value))))
            except Exception:
                vtxt = "--"
        val_scale = 0.52
        vy = int(cy + r * 0.38)  # 中心より少し下（ゲージ内）
        self._center_text(img, vtxt, cx, vy, val_scale, TEXT, thickness=1, outline=2)

        # ラベル（少し小さく＆下に出すが、余白を小さく）
        label_scale = 0.46
        (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, label_scale, 1)
        lx = int(cx - tw // 2)
        ly = int(cy + r + th + 2)
        self._blend_rect(img, lx - 4, ly - th - 4, lx + tw + 4, ly + 4, alpha=0.14)
        self._put_outline(img, label_text, (lx, ly), label_scale, CYAN, thickness=1, outline=2)

    def _bar(self, img, x, y, w, h, ratio):
        cv2.rectangle(img, (x, y), (x + w, y + h), (230, 230, 230), -1)
        cv2.rectangle(img, (x, y), (x + w, y + h), (160, 160, 160), 1)

        if ratio is None:
            return
        r = float(ratio)
        r = max(0.0, min(1.0, r))
        fh = int(h * r)
        if fh > 0:
            cv2.rectangle(img, (x, y + (h - fh)), (x + w, y + h), (0, 0, 0), -1)

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
        sn=None,
        temp=None,
        flight_time=None,
        agx=None, agy=None, agz=None,
        speed=None,
        wifi=None,
        commands=None,
    ):
        h, w, _ = frame.shape
        canvas = frame.copy()

        s = max(0.6, min(1.10, w / 900.0))

        # 左上：SN
        sn_text = f"SN: {sn if sn is not None else '--'}"
        self._boxed_text(canvas, sn_text, int(14 * s), int(38 * s), 0.90 * s, TEXT, pad=6, thickness=1, outline=2, alpha=0.18)

        # 右上：TEMP/time
        ttemp = "--" if temp is None else str(int(temp))
        ttime = "--" if flight_time is None else str(int(flight_time))
        top_line = f"TEMP:{ttemp}   time:{ttime}s"
        self._blend_rect(canvas, int(w * 0.56), 0, w, int(48 * s), alpha=0.18)
        self._put_right_outline(canvas, top_line, int(w - 14 * s), int(36 * s), 0.80 * s, TEXT, thickness=1, outline=2)

        # ゲージ：2列×3行（ここは現状維持、重なりは“数値を中へ”で解消）
        margin = int(18 * s)
        gap_x = int(30 * s)
        gap_y = int(44 * s)

        base = min(w, h)
        r = int(base * 0.052)
        r = max(34, min(r, 54))

        cols, rows = 2, 3
        block_w = cols * (2 * r) + (cols - 1) * gap_x
        block_h = rows * (2 * r) + (rows - 1) * gap_y

        block_x0 = w - margin - block_w
        block_y0 = int(74 * s)

        self._blend_rect(
            canvas,
            block_x0 - int(16 * s),
            block_y0 - int(34 * s),
            w - margin + int(16 * s),
            block_y0 + block_h + int(150 * s),
            alpha=0.12
        )

        gauge_specs = [
            ("ROLL (X)",  roll,  -90,  90),
            ("PITCH (Y)", pitch, -90,  90),
            ("YAW (Z)",   yaw,  -180, 180),
            ("ACC (X)",   agx,  -500, 500),
            ("ACC (Y)",   agy,  -500, 500),
            ("ACC (Z)",   agz,  -500, 500),
        ]

        idx = 0
        for rr in range(rows):
            cy = block_y0 + rr * ((2 * r) + gap_y) + r
            for cc in range(cols):
                cx = block_x0 + cc * ((2 * r) + gap_x) + r
                label, val, vmin, vmax = gauge_specs[idx]
                self._neon_gauge(canvas, (cx, cy), r, val, vmin, vmax, label)
                idx += 1

        # バー：右端から逆算して画面内に固定
        bar_gap = int(30 * s)
        bar_w = int(30 * s)
        bar_w = max(20, min(bar_w, 40))

        bar_top = block_y0 + block_h + int(30 * s)

        bottom_reserved = int(86 * s)
        label_space = int(42 * s)
        max_bar_h = max(70, (h - bottom_reserved) - (bar_top + label_space))
        bar_h = min(int(170 * s), max_bar_h)

        right_edge = w - margin - int(10 * s)  # 少し内側に寄せて切れ防止
        bx3 = right_edge - bar_w
        bx2 = bx3 - bar_gap - bar_w
        bx1 = bx2 - bar_gap - bar_w

        alt_ratio = None if height is None else max(0.0, min(1.0, float(height) / 300.0))
        spd_ratio = None if speed is None else max(0.0, min(1.0, float(speed) / 100.0))
        bat_ratio = None if battery is None else max(0.0, min(1.0, float(battery) / 100.0))

        self._bar(canvas, bx1, bar_top, bar_w, bar_h, alt_ratio)
        self._bar(canvas, bx2, bar_top, bar_w, bar_h, spd_ratio)
        self._bar(canvas, bx3, bar_top, bar_w, bar_h, bat_ratio)

        label_y = bar_top + bar_h + int(28 * s)
        alt_label, alt_val = "ALT", (f"{int(height)}cm" if height is not None else "--")
        spd_label, spd_val = "SPD", (f"{int(speed)}" if speed is not None else "--")
        bat_label, bat_val = "BAT", (f"{int(battery)}%" if battery is not None else "--%")


        self._blend_rect(canvas, bx1 - int(12 * s), label_y - int(22 * s),
                         right_edge + int(12 * s), label_y + int(14 * s), alpha=0.14)
        
        label_y = bar_top + bar_h + int(24 * s)   # ラベル行
        value_y = label_y + int(22 * s)           # 値行（ここで改行の間隔）

        self._center_text(canvas, alt_label, bx1 + bar_w // 2, label_y, 0.58 * s, TEXT, thickness=1, outline=2)
        self._center_text(canvas, alt_val,   bx1 + bar_w // 2, value_y, 0.64 * s, TEXT, thickness=1, outline=2)

        self._center_text(canvas, spd_label, bx2 + bar_w // 2, label_y, 0.58 * s, TEXT, thickness=1, outline=2)
        self._center_text(canvas, spd_val,   bx2 + bar_w // 2, value_y, 0.64 * s, TEXT, thickness=1, outline=2)

        self._center_text(canvas, bat_label, bx3 + bar_w // 2, label_y, 0.58 * s, TEXT, thickness=1, outline=2)
        self._center_text(canvas, bat_val,   bx3 + bar_w // 2, value_y, 0.64 * s, TEXT, thickness=1, outline=2)



        # 右下：wifi
        wifi_txt = f"wifi:{wifi if wifi is not None else '--'}"
        self._boxed_text(canvas, wifi_txt, int(w - 230 * s), int(h - 14 * s), 0.50 * s, TEXT,
                         pad=6, thickness=1, outline=2, alpha=0.14)

        # 左下：コマンド
        if commands is None:
            commands = "[T]takeoff  [G]land  [W/A/S/D]move  [R/F]up/down  [E/Q]yaw  [Z]quit"
        self._blend_rect(canvas, 0, int(h - 66 * s), int(w * 0.50), h, alpha=0.14)
        self._put_outline(canvas, commands, (int(14 * s), int(h - 22 * s)), 0.50 * s, TEXT, thickness=1, outline=2)

        return canvas
