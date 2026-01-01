from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class Settings:
    # 音效
    sound_path: str = "萝卜（Feat. JZY）.mp3"
    enable_sound: bool = True

    # 遮罩
    enable_overlay: bool = True
    overlay_seconds: float = 3.0
    overlay_alpha: float = 0.5
    overlay_text: str = "你不老实"

    # 检测参数
    thresh: float = 0.3  # 检测阈值，数值越高误报越少，自行测试
    interval_sec: float = 0.2  # 检测间隔（秒）
    consecutive_hits: int = 2  # 连续命中次数
    cooldown_sec: float = 3.0  # 触发冷却

    # 滑动窗口平滑
    smooth_window: int = 4  # 取最近 N 次概率平均（<=1 表示不平滑）

    # 截屏区域，None 表示主屏全屏
    region: Optional[Dict[str, int]] = None