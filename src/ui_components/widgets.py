# ui_components/widgets.py
import cv2
import numpy as np
from .style import (
    PANEL,
    OUTLINE,
    CYAN,
    PURPLE,
    TICK,
    TEXT,
    BAR_BASE,
    BAR_BORDER,
    BAR_FILL,
)


def blend_rect(img, x1, y1, x2, y2, alpha=0.32):
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


def put_outline(img, text, org, scale, color, thickness=1, outline=2):
    cv2.putText(img, str(text), org, cv2.FONT_HERSHEY_SIMPLEX, scale, OUTLINE, outline, cv2.LINE_AA)
    cv2.putText(img, str(text), org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def put_right_outline(img, text, right_x, y, scale, color, thickness=1, outline=2):
    (tw, _), _ = cv2.getTextSize(str(text), cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    put_outline(img, text, (int(right_x - tw), int(y)), scale, color, thickness, outline)


def boxed_text(img, text, x, y, scale, color, pad=6, thickness=1, outline=2, alpha=0.22):
    (tw, th), _ = cv2.getTextSize(str(text), cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    blend_rect(img, x - pad, y - th - pad, x + tw + pad, y + pad, alpha=alpha)
    put_outline(img, text, (x, y), scale, color, thickness, outline)


def boxed_center_multiline(
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

    step = int(max_h * line_gap)

    x1 = int(cx - max_w // 2 - pad)
    x2 = int(cx + max_w // 2 + pad)
    y1 = int(y - max_h - pad)
    y2 = int(y + (len(lines) - 1) * step + pad)
    blend_rect(img, x1, y1, x2, y2, alpha=alpha)

    for i, line in enumerate(lines):
        (tw, _), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        x = int(cx - tw // 2)
        yy = int(y + i * step)
        put_outline(img, line, (x, yy), scale, color, thickness, outline)


def neon_gauge(img, center, r, value, vmin, vmax, label_text, show_value=True, text_scale=1.0):
    cx, cy = center

    arc_thick = 1
    needle_thick = 1

    start_deg = 210
    end_deg = -30

    # arc
    cv2.ellipse(img, (cx, cy), (r, r), 0, start_deg, end_deg, (110, 110, 60), arc_thick + 1, cv2.LINE_AA)
    cv2.ellipse(img, (cx, cy), (r, r), 0, start_deg, end_deg, CYAN, arc_thick, cv2.LINE_AA)

    # ticks
    for t in np.linspace(0.18, 0.82, 4):
        ang = np.deg2rad(start_deg + (end_deg - start_deg) * t)
        x1 = int(cx + (r * 0.74) * np.cos(ang))
        y1 = int(cy - (r * 0.74) * np.sin(ang))
        x2 = int(cx + (r * 0.86) * np.cos(ang))
        y2 = int(cy - (r * 0.86) * np.sin(ang))
        cv2.line(img, (x1, y1), (x2, y2), TICK, 1, cv2.LINE_AA)

    # needle
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

    cv2.circle(img, (cx, cy), 2, PURPLE, -1, cv2.LINE_AA)

    # label
    label_scale = 0.44 * text_scale
    (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, label_scale, 1)
    lx = int(cx - tw // 2)
    ly = int(cy + r + th + 3)
    blend_rect(img, lx - 4, ly - th - 4, lx + tw + 4, ly + 4, alpha=0.16)
    put_outline(img, label_text, (lx, ly), label_scale, CYAN, thickness=1, outline=2)

    # value
    if show_value:
        val_scale = 0.40 * text_scale
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
        blend_rect(img, vx - 4, vy - th2 - 4, vx + tw2 + 4, vy + 4, alpha=0.12)
        put_outline(img, vtxt, (vx, vy), val_scale, TEXT, thickness=1, outline=2)


def bar(img, x, y, w, h, ratio):
    # ベースと枠をグレーで塗り、充填部分もグレー系に寄せる
    cv2.rectangle(img, (x, y), (x + w, y + h), BAR_BASE, -1)
    cv2.rectangle(img, (x, y), (x + w, y + h), BAR_BORDER, 1)

    if ratio is None:
        return
    r = float(ratio)
    r = max(0.0, min(1.0, r))
    fh = int(h * r)
    if fh > 0:
        cv2.rectangle(img, (x, y + (h - fh)), (x + w, y + h), BAR_FILL, -1)


def draw_position_map(
    img,
    x,
    y,
    w,
    h,
    pos_xy,
    *,
    max_range=3.0,
    yaw_deg=None,
    alpha=0.16,
    label=None,
):
    """シンプルな位置インジケーター。Xは左右、Yは上から下方向に進む。"""
    blend_rect(img, x, y, x + w, y + h, alpha=alpha)
    cv2.rectangle(img, (x, y), (x + w, y + h), BAR_BORDER, 1, cv2.LINE_AA)

    cx = x + w // 2
    top = y + 8
    bot = y + h - 8

    # ガイドライン（縦線とスタートライン）
    cv2.line(img, (cx, top), (cx, bot), TICK, 1, cv2.LINE_AA)
    cv2.line(img, (x + 6, top), (x + w - 6, top), TICK, 1, cv2.LINE_AA)

    # 位置をスケールしてプロット（Yは上が初期位置）
    px, py = pos_xy if pos_xy is not None else (0.0, 0.0)
    try:
        px = float(px)
        py = float(py)
    except Exception:
        px = py = 0.0

    try:
        if isinstance(max_range, (list, tuple)) and len(max_range) == 2:
            range_x = float(max_range[0])
            range_y = float(max_range[1])
        else:
            r = float(max_range)
            range_x = r
            range_y = r
    except Exception:
        range_x = 3.0
        range_y = 3.0

    range_x = max(range_x, 0.1)
    range_y = max(range_y, 0.1)

    px = max(-range_x, min(range_x, px))
    py = max(-range_y, min(range_y, py))

    scale_x = (w * 0.46) / range_x
    scale_y = (h * 0.78) / range_y

    dot_x = int(cx + px * scale_x)
    dot_y = int(top + py * scale_y)

    cv2.circle(img, (dot_x, dot_y), 5, PURPLE, -1, cv2.LINE_AA)
    cv2.circle(img, (dot_x, dot_y), 7, OUTLINE, 1, cv2.LINE_AA)
    if yaw_deg is not None:
        try:
            angle = np.deg2rad(float(yaw_deg))
            arrow_len = max(10, int(min(w, h) * 0.08))
            dx = int(np.sin(angle) * arrow_len)
            dy = int(np.cos(angle) * arrow_len)
            cv2.arrowedLine(
                img,
                (dot_x, dot_y),
                (dot_x + dx, dot_y + dy),
                PURPLE,
                2,
                cv2.LINE_AA,
                tipLength=0.4,
            )
        except Exception:
            pass

    if label:
        put_outline(img, label, (x + 6, y + h - 6), 0.42, TEXT, thickness=1, outline=2)
