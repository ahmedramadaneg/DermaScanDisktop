"""Webcam access with OpenCV, driven by a Qt timer (no extra threads needed)."""
import os

import cv2
from PySide6.QtCore import QObject, QTimer, Signal

# DirectShow is the fastest/most reliable backend on Windows.
BACKEND = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY


def list_cameras(max_index: int = 6):
    """Probe the first few device indexes and return the ones that open."""
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, BACKEND)
        if cap.isOpened():
            found.append(i)
        cap.release()
    return found


class CameraController(QObject):
    frame_ready = Signal(object)  # BGR numpy frame
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cap = None
        self.last_frame = None
        self._fails = 0
        self.timer = QTimer(self)
        self.timer.setInterval(33)  # ~30 fps
        self.timer.timeout.connect(self._tick)

    def start(self, index: int) -> bool:
        self.stop()
        cap = cv2.VideoCapture(index, BACKEND)
        if not cap.isOpened():
            cap.release()
            self.error.emit(f"Could not open camera {index}. Is it in use by another app?")
            return False
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap, self._fails, self.last_frame = cap, 0, None
        self.timer.start()
        return True

    def pause(self):
        self.timer.stop()

    def resume(self):
        if self.cap is not None:
            self._fails = 0
            self.timer.start()

    def stop(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
        self.cap, self.last_frame = None, None

    def _tick(self):
        ok, frame = self.cap.read()
        if not ok:
            self._fails += 1
            if self._fails > 30:
                self.stop()
                self.error.emit("The camera stopped sending frames (unplugged?).")
            return
        self._fails = 0
        self.last_frame = frame
        self.frame_ready.emit(frame)
