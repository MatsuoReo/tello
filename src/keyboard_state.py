# keyboard_state.py
from pynput import keyboard


class KeyboardState:
    def __init__(self):
        # 今押されているキーの集合（文字1文字の str）
        self.pressed = set()

        # リスナーを開始（別スレッドで動く）
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()

    def _on_press(self, key):
        # 1. 通常の文字キー（w, a, s, d など）
        if isinstance(key, keyboard.KeyCode):
            if key.char is not None:
                ch = key.char.lower()          # ★ 常に小文字にそろえる
                self.pressed.add(ch)
            return

        # 2. 特殊キー（Shift, Space など）
        #    好きな名前で登録しておく
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.pressed.add("shift")
        elif key == keyboard.Key.space:
            self.pressed.add("space")

    def _on_release(self, key):
        # 1. 文字キー
        if isinstance(key, keyboard.KeyCode):
            if key.char is not None:
                ch = key.char.lower()          # ★ ここも小文字に
                self.pressed.discard(ch)
            return

        # 2. 特殊キー
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.pressed.discard("shift")
        elif key == keyboard.Key.space:
            self.pressed.discard("space")

    def is_pressed(self, name: str) -> bool:
        """name は 'w', 'a', 'shift', 'space' など"""
        return name in self.pressed
