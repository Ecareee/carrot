import ctypes
import os
import queue
import time

from playsound3 import playsound


class OverlayManager:
    def __init__(self):
        self._queue = queue.Queue()
        self._root = None
        self._label = None
        self._deadline = 0.0
        self._alpha = 0.35
        self._text = "内容提醒"
        self._hwnd = None
        self._user32 = None

    def show(self, duration_s: float, alpha: float, text: str):
        """线程安全：发送显示请求到队列"""
        self._queue.put(("show", duration_s, alpha, text))

    def hide(self):
        """线程安全：发送隐藏请求"""
        self._queue.put(("hide",))

    def mainloop(self):
        """在主线程运行 tk"""
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.configure(bg="black")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0)

        user32 = ctypes.windll.user32
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        root.geometry(f"{w}x{h}+0+0")

        label = tk.Label(
            root,
            text="",
            fg="white",
            bg="black",
            font=("Microsoft YaHei", 50, "bold"),
        )
        label.pack(expand=True)

        self._root = root
        self._label = label
        self._user32 = user32

        self._setup_window_style()

        def poll_queue():
            """定时检查队列消息"""
            try:
                while True:
                    msg = self._queue.get_nowait()
                    if msg[0] == "show":
                        _, duration_s, alpha, text = msg
                        self._do_show(duration_s, alpha, text)
                    elif msg[0] == "hide":
                        self._do_hide()
                    elif msg[0] == "quit":
                        root.destroy()
                        return
            except queue.Empty:
                pass

            if 0 < self._deadline <= time.time():
                self._do_hide()

            root.after(50, poll_queue)

        root.after(50, poll_queue)

        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass

    def _setup_window_style(self):
        """窗口透明 + 鼠标穿透"""
        root = self._root

        root.attributes("-alpha", 0)
        root.deiconify()
        root.update()

        GA_ROOT = 2
        inner_hwnd = root.winfo_id()
        hwnd = self._user32.GetAncestor(inner_hwnd, GA_ROOT)

        if hwnd == 0:
            hwnd = inner_hwnd
            while True:
                parent = self._user32.GetParent(hwnd)
                if parent == 0:
                    break
                hwnd = parent

        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_TOOLWINDOW = 0x00000080  # 不在任务栏显示

        exstyle = self._user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        new_style = exstyle | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
        self._user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)

        self._hwnd = hwnd
        root.withdraw()

    def _do_show(self, duration_s: float, alpha: float, text: str):
        """实际显示遮罩（主线程调用）"""
        self._alpha = alpha
        self._text = text
        self._deadline = max(self._deadline, time.time() + duration_s)

        self._label.config(text=text)
        self._root.deiconify()
        self._root.lift()
        self._root.attributes("-topmost", True)

        LWA_ALPHA = 0x02
        alpha_byte = int(alpha * 255)
        self._user32.SetLayeredWindowAttributes(self._hwnd, 0, alpha_byte, LWA_ALPHA)

    def _do_hide(self):
        """实际隐藏遮罩（主线程调用）"""
        self._deadline = 0.0
        self._root.withdraw()


class SoundPlayer:
    def __init__(self, sound_path: str):
        self.sound_path = sound_path
        self._obj = None

    def play(self):
        if not os.path.exists(self.sound_path):
            return
        try:
            if self._obj is not None and self._obj.is_alive():
                self._obj.stop()
            self._obj = playsound(self.sound_path, block=False)
        except Exception:
            pass
