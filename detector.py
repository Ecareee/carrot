import time
from collections import deque
from typing import Optional, Dict

import mss
import numpy as np
import opennsfw2 as n2
from PIL import Image


class ScreenNSFWDetector:

    def __init__(self, smooth_window: int = 4):
        self.model = n2.make_open_nsfw_model()
        self.smooth_window = max(1, int(smooth_window))
        self._hist = deque(maxlen=self.smooth_window)

    @staticmethod
    def _grab_pil(sct: mss.mss, monitor: Dict) -> Image.Image:
        sct_img = sct.grab(monitor)
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    def predict_nsfw_prob(self, pil_img: Image.Image) -> float:
        arr = n2.preprocess_image(pil_img, n2.Preprocessing.YAHOO)
        inputs = np.expand_dims(arr, axis=0)
        sfw_p, nsfw_p = self.model.predict(inputs, verbose=0)[0]
        p = float(nsfw_p)

        self._hist.append(p)
        if self.smooth_window <= 1:
            return p
        return float(sum(self._hist) / len(self._hist))

    def loop(
            self,
            interval_sec: float,
            region: Optional[Dict[str, int]] = None,
    ):
        with mss.mss() as sct:
            monitor = region if region is not None else sct.monitors[1]
            while True:
                t0 = time.time()
                pil = self._grab_pil(sct, monitor)
                p = self.predict_nsfw_prob(pil)
                yield p, t0

                # 节流
                dt = time.time() - t0
                sleep_for = max(0.0, float(interval_sec) - dt)
                time.sleep(sleep_for)
