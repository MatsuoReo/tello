# ui_components/drone_ui.py
import cv2
import numpy as np

from .layout import compose_side
from .style import TEXT
from .config import (
    S_MIN, S_MAX, S_BASE_W,
    HUD_SN_X, HUD_SN_Y, HUD_SN_SCALE, HUD_SN_ALPHA,
    HUD_TOP_RIGHT_PAD_X, HUD_TOP_Y, HUD_TOP_PAD, HUD_TOP_SCALE, HUD_TOP_ALPHA,
    HUD_WIFI_RIGHT_INSET, HUD_WIFI_BOTTOM_INSET, HUD_WIFI_SCALE, HUD_WIFI_ALPHA,
    HUD_CMD_X, HUD_CMD_BOTTOM_INSET, HUD_CMD_PAD, HUD_CMD_SCALE, HUD_CMD_ALPHA,
    PANEL_COLS, PANEL_ROWS,
    PANEL_MARGIN, GAUGE_GAP_X, GAUGE_GAP_Y,
    PANEL_BLOCK_TOP, PANEL_BOTTOM_RESERVED,
    GAUGE_MIN_R,
    GAUGE_BG_PAD_X, GAUGE_BG_PAD_TOP, GAUGE_BG_PAD_BOTTOM, GAUGE_BG_ALPHA,
    GAUGE_TO_BAR_GAP,
    BAR_GAP, BAR_MIN_W,
    BAR_LABEL_SPACE, BAR_BOTTOM_PAD,
    BAR_H_RATIO, BAR_MIN_H,
    BAR_LABEL_SCALE, BAR_LABEL_Y_GAP, BAR_LABEL_PAD, BAR_LABEL_ALPHA,
)
from .widgets import (
    blend_rect,
    boxed_text,
    boxed_center_multiline,
    put_right_outline,
    put_outline,
    neon_gauge,
    bar,
    draw_position_map,
)


def _calc_s(w: int) -> float:
    return max(S_MIN, min(S_MAX, float(w) / S_BASE_W))


class DroneUI:
    def __init__(self, panel_width: int = 260, bottom_margin: int = 60, text_scale: float = 1.05):
        self.panel_width = panel_width
        self.bottom_margin = bottom_margin
        self.text_scale = text_scale

        self.crosshair_enabled = True
        self.crosshair_y_offset = 0   # +で下、-で上（px）
        self.crosshair_size = 12      # 十字の半径（px）
        self.crosshair_thickness = 1  # 線の太さ

    def compose_side(
        self,
        frame,
        *,
        display_w: int,
        display_h: int,
        ui_w: int = 260,
        ui_bg=(0, 0, 0),
        **telemetry,
    ):
        return compose_side(
            self,
            frame,
            display_w,
            display_h,
            ui_w=ui_w,
            ui_bg=ui_bg,
            **telemetry,
        )
    


    # -----------------------------
    # 左（映像）側に出したいHUD
    # -----------------------------
    def _render_hud_left(
        self,
        canvas,
        *,
        aruno=None,
        aruno_last=None,
        temp=None,
        flight_time=None,
        wifi=None,
        commands=None,
    ):
        h, w, _ = canvas.shape
        s = _calc_s(w)
        ts = self.text_scale

        # 左上 ArUco（ArUno）
        aruno_text = f"ArUno: {aruno if aruno is not None else '--'}  last:{aruno_last if aruno_last is not None else '--'}"
        boxed_text(
            canvas,
            aruno_text,
            int(HUD_SN_X * s),
            int(HUD_SN_Y * s),
            HUD_SN_SCALE * s * ts,
            TEXT,
            pad=6,
            thickness=1,
            outline=2,
            alpha=HUD_SN_ALPHA,
        )

        # 右上 TEMP/time
        ttemp = "--" if temp is None else str(int(temp))
        ttime = "--" if flight_time is None else str(int(flight_time))
        top_line = f"TEMP:{ttemp}   time:{ttime}s"

        top_scale = HUD_TOP_SCALE * s * ts
        pad = int(HUD_TOP_PAD * s)
        x_right = int(w - HUD_TOP_RIGHT_PAD_X * s)
        y_base = int(HUD_TOP_Y * s)

        (tw, th), _ = cv2.getTextSize(top_line, cv2.FONT_HERSHEY_SIMPLEX, top_scale, 1)
        x1 = x_right - tw - pad
        y1 = y_base - th - pad
        x2 = x_right + pad
        y2 = y_base + pad
        blend_rect(canvas, x1, y1, x2, y2, alpha=HUD_TOP_ALPHA)
        put_right_outline(canvas, top_line, x_right, y_base, top_scale, TEXT, thickness=1, outline=2)

        # 右下 wifi
        wifi_txt = f"wifi:{wifi if wifi is not None else '--'}"
        boxed_text(
            canvas,
            wifi_txt,
            int(w - HUD_WIFI_RIGHT_INSET * s),
            int(h - HUD_WIFI_BOTTOM_INSET * s),
            HUD_WIFI_SCALE * s * ts,
            TEXT,
            pad=6,
            thickness=1,
            outline=2,
            alpha=HUD_WIFI_ALPHA,
        )

        # 左下 コマンド
        if commands is None:
            commands = "[T]takeoff  [G]land  [W/A/S/D]move  [R/F]up/down  [E/Q]yaw  [Z]quit"

        cmd_scale = HUD_CMD_SCALE * s * ts
        x = int(HUD_CMD_X * s)
        y = int(h - HUD_CMD_BOTTOM_INSET * s)

        (tw2, th2), _ = cv2.getTextSize(commands, cv2.FONT_HERSHEY_SIMPLEX, cmd_scale, 1)
        pad2 = int(HUD_CMD_PAD * s)
        blend_rect(canvas, x - pad2, y - th2 - pad2, x + tw2 + pad2, y + pad2, alpha=HUD_CMD_ALPHA)
        put_outline(canvas, commands, (x, y), cmd_scale, TEXT, thickness=1, outline=2)

                # ===== Crosshair (center) =====
        if getattr(self, "crosshair_enabled", True):
            cx = w // 2
            cy = h // 2 + int(getattr(self, "crosshair_y_offset", 0))

            size = int(getattr(self, "crosshair_size", 12))
            thick = int(getattr(self, "crosshair_thickness", 1))

            # 目立たせるために「縁取り → 本線」
            # 中心点
            cv2.circle(canvas, (cx, cy), max(2, thick + 2), (0, 0, 0), -1, cv2.LINE_AA)
            cv2.circle(canvas, (cx, cy), max(1, thick), (255, 255, 120), -1, cv2.LINE_AA)  # CYANっぽい

            # 横線
            cv2.line(canvas, (cx - size, cy), (cx + size, cy), (0, 0, 0), thick + 2, cv2.LINE_AA)
            cv2.line(canvas, (cx - size, cy), (cx + size, cy), (255, 255, 120), thick, cv2.LINE_AA)

            # 縦線
            cv2.line(canvas, (cx, cy - size), (cx, cy + size), (0, 0, 0), thick + 2, cv2.LINE_AA)
            cv2.line(canvas, (cx, cy - size), (cx, cy + size), (255, 255, 120), thick, cv2.LINE_AA)


        return canvas

    # -----------------------------
    # 右（UIパネル）側：メーター/バーのみ
    # -----------------------------
    def _render_ui_panel(
        self,
        canvas,
        *,
        battery=None,
        roll=None,
        pitch=None,
        yaw=None,
        height=None,
        total_alt=None,
        agx=None, agy=None, agz=None,
        speed=None,
        pos_xy=None,
        pos_range=3.0,
    ):
        h, w, _ = canvas.shape
        s = _calc_s(w)
        ts = self.text_scale

        cols, rows = PANEL_COLS, PANEL_ROWS

        margin = int(PANEL_MARGIN * s)
        gap_x = int(GAUGE_GAP_X * s)
        gap_y = int(GAUGE_GAP_Y * s)

        block_y0 = int(PANEL_BLOCK_TOP * s)

        bottom_reserved = int(PANEL_BOTTOM_RESERVED * s)
        avail_h = max(1, h - block_y0 - bottom_reserved)

        r_w = (w - 2 * margin - (cols - 1) * gap_x) // (2 * cols)
        r_h = (avail_h - (rows - 1) * gap_y) // (2 * rows)
        r = int(max(GAUGE_MIN_R, min(r_w, r_h)))

        block_w = cols * (2 * r) + (cols - 1) * gap_x
        block_h = rows * (2 * r) + (rows - 1) * gap_y
        block_x0 = w - margin - block_w

        blend_rect(
            canvas,
            block_x0 - int(GAUGE_BG_PAD_X * s),
            block_y0 - int(GAUGE_BG_PAD_TOP * s),
            w - margin + int(GAUGE_BG_PAD_X * s),
            block_y0 + block_h + int(GAUGE_BG_PAD_BOTTOM * s),
            alpha=GAUGE_BG_ALPHA,
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
                neon_gauge(canvas, (cx, cy), r, val, vmin, vmax, label, show_value=True, text_scale=ts)
                idx += 1

        # ===== バー =====
        gauge_to_bar_gap = int(GAUGE_TO_BAR_GAP * s)
        bar_top = block_y0 + block_h + gauge_to_bar_gap

        # バーを圧縮しつつ少しだけ余裕を追加して左寄せ配置
        bar_gap = int(BAR_GAP * s * 0.25)
        base_bar_w = (w - 2 * margin - 2 * bar_gap) // 3
        bar_w = int(max(BAR_MIN_W, base_bar_w * 0.40))

        label_space = int(BAR_LABEL_SPACE * s)
        bar_h_max = h - (bar_top + label_space + int(BAR_BOTTOM_PAD * s))
        bar_h = int(max(BAR_MIN_H, min(int(h * BAR_H_RATIO), bar_h_max)))

        left_edge = margin
        bx1 = left_edge
        bx2 = bx1 + bar_w + bar_gap
        bx3 = bx2 + bar_w + bar_gap

        alt_ratio = None if height is None else max(0.0, min(1.0, float(height) / 300.0))
        spd_ratio = None if speed is None else max(0.0, min(1.0, float(speed) / 100.0))
        bat_ratio = None if battery is None else max(0.0, min(1.0, float(battery) / 100.0))

        bar(canvas, bx1, bar_top, bar_w, bar_h, alt_ratio)
        bar(canvas, bx2, bar_top, bar_w, bar_h, spd_ratio)
        bar(canvas, bx3, bar_top, bar_w, bar_h, bat_ratio)

        # ===== 位置インジケーター（バー右の空きスペース活用）=====
        map_x0 = bx3 + bar_w + bar_gap
        map_w = w - margin - map_x0
        if map_w < 50:
            map_w = max(50, int(bar_w * 1.1))
            map_x0 = w - margin - map_w
        map_h = bar_h
        pos_label = None
        if pos_xy is not None:
            try:
                pos_label = f"X:{float(pos_xy[0]):+.2f}  Y:{float(pos_xy[1]):+.2f}"
            except Exception:
                pos_label = None
        draw_position_map(
            canvas,
            map_x0,
            bar_top,
            map_w,
            map_h,
            pos_xy,
            max_range=max(pos_range, 0.1),
            label=pos_label,
        )

        # ===== バーラベル（改行）=====
        label_scale = BAR_LABEL_SCALE * s * ts
        alt_val = "--" if height is None else str(int(height))
        spd_val = "--" if speed is None else str(int(speed))
        bat_val = "--%" if battery is None else f"{int(battery)}%"

        alt_txt = f"ALT\n{alt_val}"
        spd_txt = f"SPD\n{spd_val}"
        bat_txt = f"BAT\n{bat_val}"

        label_y1 = bar_top + bar_h + int(BAR_LABEL_Y_GAP * s)

        boxed_center_multiline(
            canvas, alt_txt, bx1 + bar_w // 2, label_y1, label_scale, TEXT,
            pad=int(BAR_LABEL_PAD * s), alpha=BAR_LABEL_ALPHA
        )
        boxed_center_multiline(
            canvas, spd_txt, bx2 + bar_w // 2, label_y1, label_scale, TEXT,
            pad=int(BAR_LABEL_PAD * s), alpha=BAR_LABEL_ALPHA
        )
        boxed_center_multiline(
            canvas, bat_txt, bx3 + bar_w // 2, label_y1, label_scale, TEXT,
            pad=int(BAR_LABEL_PAD * s), alpha=BAR_LABEL_ALPHA
        )

        return canvas

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
        aruno=None,
        aruno_last=None,
        temp=None,
        flight_time=None,
        agx=None, agy=None, agz=None,
        speed=None,
        pos_xy=None,
        pos_range=3.0,
        wifi=None,
        commands=None,
        layout="side",
        ui_bg=(245, 245, 245),
        ui_width=None,
    ):
        h, w, _ = frame.shape

        if layout == "overlay":
            canvas = frame.copy()
            self._render_hud_left(
            canvas,
            aruno=aruno,
            aruno_last=aruno_last,
            temp=temp,
            flight_time=flight_time,
            wifi=wifi,
            commands=commands,
        )
            return canvas

        left = frame.copy()
        self._render_hud_left(
            left,
            aruno=aruno,
            aruno_last=aruno_last,
            temp=temp,
            flight_time=flight_time,
            wifi=wifi,
            commands=commands,
        )

        ui_w = w if ui_width is None else int(ui_width)
        panel = np.full((h, ui_w, 3), ui_bg, dtype=frame.dtype)

        self._render_ui_panel(
            panel,
            battery=battery,
            roll=roll,
            pitch=pitch,
            yaw=yaw,
            height=height,
            total_alt=total_alt,
            agx=agx, agy=agy, agz=agz,
            speed=speed,
            pos_xy=pos_xy,
            pos_range=pos_range,
        )

        return np.hstack([left, panel])
