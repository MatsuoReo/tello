# display_manager.py
import cv2
import numpy as np


class DisplayManager:
    def __init__(
        self,
        window_name: str = "Tello UI",
        init_w: int = 1600,
        init_h: int = 900,
        fullscreen: bool = True,
        ui_ratio: float = 0.22,
        ui_min: int = 260,
        ui_max: int = 700,
    ):
        self.window_name = window_name
        self.init_w = init_w
        self.init_h = init_h
        self.fullscreen = fullscreen

        self.ui_ratio = ui_ratio
        self.ui_min = ui_min
        self.ui_max = ui_max

        self.w = init_w
        self.h = init_h
        self.ui_w = ui_min

        self._create_window()

    def _create_window(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        try:
            cv2.resizeWindow(self.window_name, self.init_w, self.init_h)
            cv2.moveWindow(self.window_name, 0, 0)
        except Exception:
            pass

        if self.fullscreen:
            try:
                cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            except Exception:
                pass

    def _get_window_size(self):
        try:
            x, y, w, h = cv2.getWindowImageRect(self.window_name)
            if w > 0 and h > 0:
                return int(w), int(h)
        except Exception:
            pass
        return None

    def _compute_ui_w(self, display_w: int) -> int:
        ui_w = int(display_w * self.ui_ratio)
        ui_w = max(self.ui_min, min(ui_w, self.ui_max))
        return ui_w

    def update(self):
        wh = self._get_window_size()
        if wh is not None:
            self.w, self.h = wh
        self.ui_w = self._compute_ui_w(self.w)
        return self.w, self.h, self.ui_w

    @staticmethod
    def fit_exact_black(img, W, H):
        canvas = np.zeros((H, W, 3), dtype=img.dtype)
        hh = min(H, img.shape[0])
        ww = min(W, img.shape[1])
        canvas[:hh, :ww] = img[:hh, :ww]
        return canvas

    def fit(self, img):
        if img.shape[1] != self.w or img.shape[0] != self.h:
            return self.fit_exact_black(img, self.w, self.h)
        return img
