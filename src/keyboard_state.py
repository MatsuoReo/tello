# keyboard_state.py
from pynput import keyboard


class KeyboardState:
    def __init__(self):
        # 今押されているキーの集合（文字1文字の str）
        self.pressed = set()

        # リスナーを開始（別スレッドで動く）
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()

    def on_press(self, key):
        try:
            ch = key.char  # 普通のキー（'w', 'a', ' ' など）
        except AttributeError:
            # 特殊キー（space, esc など）はここに来る
            if key == keyboard.Key.space:
                ch = ' '
            else:
                return  # それ以外は無視でもOK
        self.pressed.add(ch)

    def on_release(self, key):
        try:
            ch = key.char
        except AttributeError:
            if key == keyboard.Key.space:
                ch = ' '
            else:
                return
        if ch in self.pressed:
            self.pressed.remove(ch)

    def is_pressed(self, ch: str) -> bool:
        """指定したキー(例: 'w')が押されているかどうか"""
        return ch in self.pressed
