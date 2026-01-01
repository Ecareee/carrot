import ctypes
import os

# dpi 感知，解决高分屏缩放问题
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import time
import threading
from datetime import datetime

from config import Settings
from detector import ScreenNSFWDetector
from effects import OverlayManager, SoundPlayer


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def print_settings(s: Settings):
    print("守卫萝卜启动")
    print("配置：")
    if s.region is None:
        print("截屏范围：主屏全屏")
    else:
        r = s.region
        print(f"截屏范围：区域 left={r['left']} top={r['top']} w={r['width']} h={r['height']}")
    print(f"阈值：{s.thresh:.2f} | 连续命中：{s.consecutive_hits} | 冷却：{s.cooldown_sec:.1f}s")
    print(f"检测间隔：{s.interval_sec:.2f}s | 平滑窗口：{s.smooth_window}")
    print(
        f"遮罩：{'开' if s.enable_overlay else '关'} | {s.overlay_seconds:.1f}s | alpha={s.overlay_alpha:.2f} | 文本：{s.overlay_text}")
    print(f"音效：{'开' if s.enable_sound else '关'} | 文件：{s.sound_path}")


def detector_worker(s: Settings, overlay: OverlayManager, sound: SoundPlayer):
    print(f"[{now_str()}] 初始化模型中")
    detector = ScreenNSFWDetector(smooth_window=s.smooth_window)
    print(f"[{now_str()}] 模型就绪")

    hit_streak = 0
    last_fire = 0.0

    last_heartbeat = 0.0
    heartbeat_interval = 3.0

    for p, ts in detector.loop(interval_sec=s.interval_sec, region=s.region):
        if (ts - last_heartbeat) >= heartbeat_interval:
            last_heartbeat = ts
            since_fire = ts - last_fire if last_fire > 0 else -1
            since_fire_str = "还未触发过" if since_fire < 0 else f"{since_fire:.1f}s 前"
            print(
                f"[{now_str()}] 心跳：nsfw={p:.3f} | 连续命中={hit_streak}/{s.consecutive_hits} | 上次触发={since_fire_str}")

        if p >= s.thresh:
            hit_streak += 1
        else:
            hit_streak = 0

        now = time.time()
        ready = (hit_streak >= s.consecutive_hits) and ((now - last_fire) >= s.cooldown_sec)

        if ready:
            last_fire = now
            hit_streak = 0
            print(f"[{now_str()}] 触发：nsfw={p:.3f} >= {s.thresh:.2f}")

            if s.enable_overlay:
                overlay.show(s.overlay_seconds, s.overlay_alpha, s.overlay_text)

            if s.enable_sound:
                sound.play()


if __name__ == "__main__":
    s = Settings()
    overlay = OverlayManager()
    sound = SoundPlayer(s.sound_path)

    if s.enable_sound and not os.path.exists(s.sound_path):
        print(f"[{now_str()}] 找不到音效文件：{os.path.abspath(s.sound_path)}")
        print(f"[{now_str()}] 已自动关闭音效")
        s.enable_sound = False

    print_settings(s)

    t = threading.Thread(target=detector_worker, args=(s, overlay, sound), daemon=True)
    t.start()

    try:
        overlay.mainloop()
    except KeyboardInterrupt:
        print(f"\n[{now_str()}] 收到 Ctrl+C，退出")