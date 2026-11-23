"""Reusable widgets: image view, drag-and-drop zone, banner, results panel."""
import numpy as np
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar,
                               QSizePolicy, QVBoxLayout, QWidget)

SUPPORTED_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def repolish(w: QWidget):
    """Re-apply the stylesheet after changing a dynamic property."""
    w.style().unpolish(w)
    w.style().polish(w)


# Friendly names + concern level for the HAM10000 classes. Unknown labels fall back gracefully.
CLASS_INFO = {
    "akiec": ("Actinic keratosis / intraepithelial carcinoma", "moderate"),
    "bcc": ("Basal cell carcinoma", "high"),
    "bkl": ("Benign keratosis-like lesion", "low"),
    "df": ("Dermatofibroma", "low"),
    "mel": ("Melanoma", "high"),
    "nv": ("Melanocytic nevus (common mole)", "low"),
    "vasc": ("Vascular lesion", "low"),
}
RISK_TEXT = {
    "high": "Higher-concern category - please consult a dermatologist",
    "moderate": "Pre-cancerous / moderate concern - consult a dermatologist",
    "low": "Usually benign - monitor changes and see a doctor if unsure",
    "unknown": "Please consult a dermatologist",
}


class Banner(QLabel):
    """Non-blocking message strip that hides itself after a few seconds."""

    def __init__(self):
        super().__init__()
        self.setObjectName("banner")
        self.setWordWrap(True)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, level: str = "info", seconds: int = 7):
        self.setText(text)
        self.setProperty("level", level)
        repolish(self)
        self.show()
        self._timer.start(seconds * 1000)


class ImageView(QLabel):
    """Shows an RGB numpy image scaled to fit while keeping aspect ratio."""

    def __init__(self, placeholder: str = ""):
        super().__init__(placeholder)
        self.setObjectName("imageView")
        self._placeholder = placeholder
        self._pix = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumSize(260, 220)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

    def set_rgb(self, rgb: np.ndarray):
        rgb = np.ascontiguousarray(rgb)
        h, w, _ = rgb.shape
        img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        self._pix = QPixmap.fromImage(img)
        self.setProperty("filled", True)
        repolish(self)
        self._refresh()

    def clear_image(self):
        self._pix = None
        self.setPixmap(QPixmap())
        self.setText(self._placeholder)
        self.setProperty("filled", False)
        repolish(self)

    def _refresh(self):
        if self._pix is not None:
            self.setPixmap(self._pix.scaled(self.size() - QSize(6, 6),
                                            Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refresh()


class DropZone(ImageView):
    """ImageView that accepts dragged image files and opens a browser on click."""
    file_dropped = Signal(str)
    browse_requested = Signal()

    def __init__(self, placeholder: str):
        super().__init__(placeholder)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @staticmethod
    def _first_image(event):
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith(SUPPORTED_EXT):
                return p
        return None

    def dragEnterEvent(self, e):
        if self._first_image(e):
            e.acceptProposedAction()
            self.setProperty("hover", True)
            repolish(self)
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self.setProperty("hover", False)
        repolish(self)

    def dropEvent(self, e):
        self.setProperty("hover", False)
        repolish(self)
        p = self._first_image(e)
        if p:
            self.file_dropped.emit(p)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.browse_requested.emit()


class ResultsPanel(QFrame):
    """Headline prediction, concern badge, ranked probability bars, disclaimer."""

    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(10)

        t = QLabel("Analysis")
        t.setObjectName("cardTitle")
        self.headline = QLabel()
        self.headline.setObjectName("headline")
        self.headline.setWordWrap(True)
        self.sub = QLabel()
        self.sub.setObjectName("muted")
        self.sub.setWordWrap(True)
        self.badge = QLabel()
        self.badge.setObjectName("badge")
        self.badge.setWordWrap(True)

        self.bars_host = QWidget()
        self.bars = QVBoxLayout(self.bars_host)
        self.bars.setContentsMargins(0, 6, 0, 0)
        self.bars.setSpacing(7)

        self.disclaimer = QLabel(
            "<b>Educational / research prototype - not a medical diagnosis.</b> "
            "This tool cannot replace examination by a qualified dermatologist. "
            "A low-risk result never rules out skin cancer; see a doctor about any lesion "
            "that is changing, bleeding, itching or worrying you. Accuracy may vary with "
            "skin tone, lighting and image quality.")
        self.disclaimer.setObjectName("disclaimer")
        self.disclaimer.setWordWrap(True)

        for w in (t, self.headline, self.sub, self.badge, self.bars_host):
            lay.addWidget(w)
        lay.addStretch(1)
        lay.addWidget(self.disclaimer)
        self.show_placeholder()

    def _clear_bars(self):
        while self.bars.count():
            item = self.bars.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_placeholder(self, text="Load or capture an image to see results."):
        self._clear_bars()
        self.headline.setText("No result yet")
        self.sub.setText(text)
        self.badge.hide()

    def show_result(self, labels, probs, threshold: float):
        order = np.argsort(probs)[::-1]
        top = int(order[0])
        conf = float(probs[top])
        name, risk = CLASS_INFO.get(labels[top].lower(), (labels[top], "unknown"))

        if conf < threshold:
            self.headline.setText("Inconclusive")
            self.sub.setText(f"Highest score: {name} ({conf * 100:.1f}%), below the "
                             f"{threshold * 100:.0f}% confidence threshold. Try a sharper, "
                             f"well-lit, in-focus photo.")
            self.badge.setText("Please consult a dermatologist")
            self.badge.setProperty("risk", "unknown")
        else:
            self.headline.setText(name)
            self.sub.setText(f"Class '{labels[top]}'  |  confidence {conf * 100:.1f}%")
            self.badge.setText(RISK_TEXT[risk])
            self.badge.setProperty("risk", risk)
        repolish(self.badge)
        self.badge.show()

        self._clear_bars()
        for rank, i in enumerate(order):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            nm = QLabel(labels[i])
            nm.setFixedWidth(52)
            if rank == 0:
                nm.setStyleSheet("font-weight:700;")
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(int(round(float(probs[i]) * 1000)))
            bar.setTextVisible(False)
            bar.setProperty("top", rank == 0)
            pct = QLabel(f"{float(probs[i]) * 100:5.1f}%")
            pct.setFixedWidth(52)
            pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            h.addWidget(nm)
            h.addWidget(bar, 1)
            h.addWidget(pct)
            self.bars.addWidget(row)
