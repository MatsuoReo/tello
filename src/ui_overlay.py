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
    def __init__(self, panel_width: int = 260, bottom_margin: int = 60, text_scale: float = 0.85):
        self.panel_width = panel_width
        self.bottom_margin = bottom_margin
        self.text_scale = text_scale

    def _blend_rect(self, img, x1, y1, x2, y2, alpha=0.32):
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

    def _boxed_text(self, img, text, x, y, scale, color, pad=6, thickness=1, outline=2, alpha=0.22):
        (tw, th), _ = cv2.getTextSize(str(text), cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        self._blend_rect(img, x - pad, y - th - pad, x + tw + pad, y + pad, alpha=alpha)
        self._put_outline(img, text, (x, y), scale, color, thickness, outline)

    def _center_text(self, img, text, cx, y, scale, color, thickness=1, outline=2):
        (tw, _), _ = cv2.getTextSize(str(text), cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        x = int(cx - tw // 2)
        self._put_outline(img, text, (x, y), scale, color, thickness, outline)

    def _boxed_center_multiline(
        self,
        img,
        text,
        cx,
        y,
        scale,
        color,
        pad=6,
        thickness=1,
        outline=2,
        alpha=0.14,
        line_gap=1.55,
    ):
        lines = str(text).split("\n")

        sizes = [cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0] for line in lines]
        widths = [s[0] for s in sizes]
        heights = [s[1] for s in sizes]
        max_w = max(widths) if widths else 0
        max_h = max(heights) if heights else 0

        step = int(max_h * line_gap)  # baseline間隔

        # 背景（文字の領域だけ）
        x1 = int(cx - max_w // 2 - pad)
        x2 = int(cx + max_w // 2 + pad)
        y1 = int(y - max_h - pad)
        y2 = int(y + (len(lines) - 1) * step + pad)
        self._blend_rect(img, x1, y1, x2, y2, alpha=alpha)

        # 文字（各行センター）
        for i, line in enumerate(lines):
            (tw, _), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
            x = int(cx - tw // 2)
            yy = int(y + i * step)
            self._put_outline(img, line, (x, yy), scale, color, thickness, outline)

    def _neon_gauge(self, img, center, r, value, vmin, vmax, label_text, show_value=True):
        cx, cy = center

        arc_thick = 1
        needle_thick = 1

        start_deg = 210
        end_deg = -30

        # 弧（弱グロー）
        cv2.ellipse(img, (cx, cy), (r, r), 0, start_deg, end_deg, (110, 110, 60), arc_thick + 1, cv2.LINE_AA)
        cv2.ellipse(img, (cx, cy), (r, r), 0, start_deg, end_deg, CYAN, arc_thick, cv2.LINE_AA)

        # 目盛り（細い線）
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

        # ラベル（小さく）
        ts = self.text_scale
        label_scale = 0.44 * ts
        (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, label_scale, 1)
        lx = int(cx - tw // 2)
        ly = int(cy + r + th + 3)
        self._blend_rect(img, lx - 4, ly - th - 4, lx + tw + 4, ly + 4, alpha=0.16)
        self._put_outline(img, label_text, (lx, ly), label_scale, CYAN, thickness=1, outline=2)

        # 値（小さめ）
        if show_value:
            val_scale = 0.40 * ts
            if value is None:
                vtxt = "--"
            else:
                try:
                    vtxt = str(int(round(float(value))))
                except Exception:
                    vtxt = "--"
            (tw2, th2), _ = cv2.getTextSize(vtxt, cv2.FONT_HERSHEY_SIMPLEX, val_scale, 1)
            vx = int(cx - tw2 // 2)
            vy = int(ly + th2 + 3)
            self._blend_rect(img, vx - 4, vy - th2 - 4, vx + tw2 + 4, vy + 4, alpha=0.12)
            self._put_outline(img, vtxt, (vx, vy), val_scale, TEXT, thickness=1, outline=2)

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
        agx=None,
        agy=None,
        agz=None,
        speed=None,
        wifi=None,
        commands=None,
    ):
        h, w, _ = frame.shape
        canvas = frame.copy()

        s = max(0.6, min(1.10, w / 900.0))
        ts = self.text_scale

        # ===== 左上：SN =====
        sn_text = f"SN: {sn if sn is not None else '--'}"
        self._boxed_text(
            canvas,
            sn_text,
            int(14 * s),
            int(38 * s),
            0.78 * s * ts,
            TEXT,
            pad=6,
            thickness=1,
            outline=2,
            alpha=0.20,
        )

        # ===== 右上：TEMP/time（背景は文字のところだけ）=====
        ttemp = "--" if temp is None else str(int(temp))
        ttime = "--" if flight_time is None else str(int(flight_time))
        top_line = f"TEMP:{ttemp}   time:{ttime}s"

        top_scale = 0.68 * s * ts
        (tw, th), _ = cv2.getTextSize(top_line, cv2.FONT_HERSHEY_SIMPLEX, top_scale, 1)
        pad = int(10 * s)
        x_right = int(w - 14 * s)
        y_base = int(36 * s)

        x1 = x_right - tw - pad
        y1 = y_base - th - pad
        x2 = x_right + pad
        y2 = y_base + pad
        self._blend_rect(canvas, x1, y1, x2, y2, alpha=0.18)
        self._put_right_outline(canvas, top_line, x_right, y_base, top_scale, TEXT, thickness=1, outline=2)

        # ===== ゲージ：2列×3行 =====
        margin = int(18 * s)
        gap_x = int(30 * s)
        gap_y = int(50 * s)

        base = min(w, h)
        r = int(base * 0.052)
        r = max(34, min(r, 54))

        cols, rows = 2, 3
        block_w = cols * (2 * r) + (cols - 1) * gap_x
        block_h = rows * (2 * r) + (rows - 1) * gap_y

        block_x0 = w - margin - block_w
        block_y0 = int(74 * s)

        # 背景はゲージ群の周囲だけ
        self._blend_rect(
            canvas,
            block_x0 - int(16 * s),
            block_y0 - int(34 * s),
            w - margin + int(16 * s),
            block_y0 + block_h + int(150 * s),
            alpha=0.12,
        )

        gauge_specs = [
            ("ROLL (X)", roll, -90, 90),
            ("PITCH (Y)", pitch, -90, 90),
            ("YAW (Z)", yaw, -180, 180),
            ("ACC (X)", agx, -500, 500),
            ("ACC (Y)", agy, -500, 500),
            ("ACC (Z)", agz, -500, 500),
        ]

        idx = 0
        for rr in range(rows):
            cy = block_y0 + rr * ((2 * r) + gap_y) + r
            for cc in range(cols):
                cx = block_x0 + cc * ((2 * r) + gap_x) + r
                label, val, vmin, vmax = gauge_specs[idx]
                self._neon_gauge(canvas, (cx, cy), r, val, vmin, vmax, label, show_value=True)
                idx += 1

        # ===== バー（右端から逆算して必ず画面内へ）=====
        bar_gap = int(30 * s)
        bar_w = int(30 * s)
        bar_w = max(20, min(bar_w, 40))

        bar_top = block_y0 + block_h + int(30 * s)

        bottom_reserved = int(86 * s)  # コマンド帯＋余白
        label_space = int(52 * s)      # 2行ラベル分ちょい増やす
        max_bar_h = max(70, (h - bottom_reserved) - (bar_top + label_space))
        bar_h = min(int(170 * s), max_bar_h)

        right_edge = w - margin
        bx3 = right_edge - bar_w
        bx2 = bx3 - bar_gap - bar_w
        bx1 = bx2 - bar_gap - bar_w

        alt_ratio = None if height is None else max(0.0, min(1.0, float(height) / 300.0))
        spd_ratio = None if speed is None else max(0.0, min(1.0, float(speed) / 100.0))
        bat_ratio = None if battery is None else max(0.0, min(1.0, float(battery) / 100.0))

        self._bar(canvas, bx1, bar_top, bar_w, bar_h, alt_ratio)
        self._bar(canvas, bx2, bar_top, bar_w, bar_h, spd_ratio)
        self._bar(canvas, bx3, bar_top, bar_w, bar_h, bat_ratio)

        # ===== バーラベル（改行表示：ALT\nxx、BAT\nxx%）=====
        label_scale = 0.56 * s * ts

        alt_val = "--" if height is None else str(int(height))
        spd_val = "--" if speed is None else str(int(speed))
        bat_val = "--%" if battery is None else f"{int(battery)}%"

        alt_txt = f"ALT\n{alt_val}"
        spd_txt = f"SPD\n{spd_val}"
        bat_txt = f"BAT\n{bat_val}"

        label_y1 = bar_top + bar_h + int(22 * s)

        self._boxed_center_multiline(
            canvas, alt_txt, bx1 + bar_w // 2, label_y1, label_scale, TEXT, pad=int(6 * s), alpha=0.14
        )
        self._boxed_center_multiline(
            canvas, spd_txt, bx2 + bar_w // 2, label_y1, label_scale, TEXT, pad=int(6 * s), alpha=0.14
        )
        self._boxed_center_multiline(
            canvas, bat_txt, bx3 + bar_w // 2, label_y1, label_scale, TEXT, pad=int(6 * s), alpha=0.14
        )

        # ===== 右下：wifi =====
        wifi_txt = f"wifi:{wifi if wifi is not None else '--'}"
        self._boxed_text(
            canvas,
            wifi_txt,
            int(w - 230 * s),
            int(h - 14 * s),
            0.60 * s * ts,
            TEXT,
            pad=6,
            thickness=1,
            outline=2,
            alpha=0.14,
        )

        # ===== 左下：コマンド（小さく＋背景は文字部分だけ）=====
        if commands is None:
            commands = "[T]takeoff  [G]land  [W/A/S/D]move  [R/F]up/down  [E/Q]yaw  [Z]quit"

        cmd_scale = 0.56 * s * ts
        x = int(14 * s)
        y = int(h - 22 * s)

        (tw, th), _ = cv2.getTextSize(commands, cv2.FONT_HERSHEY_SIMPLEX, cmd_scale, 1)
        pad = int(10 * s)

        self._blend_rect(canvas, x - pad, y - th - pad, x + tw + pad, y + pad, alpha=0.16)
        self._put_outline(canvas, commands, (x, y), cmd_scale, TEXT, thickness=1, outline=2)

        return canvas
