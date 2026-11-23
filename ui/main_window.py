"""Main window: wires UI, camera, file loading and the classifier together."""
import cv2
import numpy as np
from PIL import Image, ImageOps
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFileDialog, QFormLayout, QFrame,
                               QHBoxLayout, QLabel, QMainWindow, QPushButton,
                               QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from core.camera import CameraController, list_cameras
from core.model import NORM_MODES, Classifier
from core.paths import find_assets
from ui.widgets import SUPPORTED_EXT, Banner, DropZone, ImageView, ResultsPanel, repolish


class SettingsDialog(QDialog):
    def __init__(self, parent, norm_mode, threshold, model_info):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(460)
        form = QFormLayout(self)
        self.norm = QComboBox()
        for key, text in NORM_MODES.items():
            self.norm.addItem(text, key)
        self.norm.setCurrentIndex(max(0, self.norm.findData(norm_mode)))
        self.thr = QDoubleSpinBox()
        self.thr.setRange(0, 100)
        self.thr.setSuffix(" %")
        self.thr.setValue(threshold * 100)
        info = QLabel(model_info)
        info.setWordWrap(True)
        info.setObjectName("muted")
        form.addRow("Input normalisation", self.norm)
        form.addRow("'Inconclusive' below", self.thr)
        form.addRow("Model", info)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DermaScan Desktop")
        self.resize(1200, 780)
        self.setMinimumSize(920, 620)

        self.cfg = QSettings("DermaScan", "Desktop")
        self.norm_mode = str(self.cfg.value("norm_mode", "mobilenet_v2"))
        self.threshold = float(self.cfg.value("threshold", 0.5))

        self.clf = Classifier()
        self.current_rgb = None
        self.cam_indices = []

        self.camera = CameraController(self)
        self.camera.frame_ready.connect(self._on_frame)
        self.camera.error.connect(lambda m: self.banner.show_message(m, "error"))

        self._build_ui()
        QTimer.singleShot(0, self._autoload)

    # ------------------------------------------------------------ UI construction
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(12)

        # Header: title, model info, status chips, load buttons
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel("DermaScan Desktop")
        t.setObjectName("title")
        self.model_info = QLabel("No model loaded")
        self.model_info.setObjectName("subtitle")
        titles.addWidget(t)
        titles.addWidget(self.model_info)
        head.addLayout(titles, 1)

        self.chip_model = QLabel("Model")
        self.chip_labels = QLabel("Labels")
        for c in (self.chip_model, self.chip_labels):
            c.setObjectName("chip")
            head.addWidget(c)
        b_model = QPushButton("Load model…")
        b_labels = QPushButton("Load labels…")
        b_set = QPushButton("Settings")
        b_model.clicked.connect(self._pick_model)
        b_labels.clicked.connect(self._pick_labels)
        b_set.clicked.connect(self._open_settings)
        for b in (b_model, b_labels, b_set):
            head.addWidget(b)
        outer.addLayout(head)

        self.banner = Banner()
        outer.addWidget(self.banner)

        # Body: input card (left) + results (right)
        body = QHBoxLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)

        left = QFrame()
        left.setObjectName("card")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(18, 16, 18, 16)
        lv.setSpacing(10)

        modes = QHBoxLayout()
        self.btn_upload = QPushButton("Upload image")
        self.btn_cam = QPushButton("Use camera")
        grp = QButtonGroup(self)
        for i, b in enumerate((self.btn_upload, self.btn_cam)):
            b.setObjectName("mode")
            b.setCheckable(True)
            grp.addButton(b, i)
            modes.addWidget(b)
        self.btn_upload.setChecked(True)
        grp.idClicked.connect(self._set_mode)
        lv.addLayout(modes)

        self.stack = QStackedWidget()
        lv.addWidget(self.stack, 1)

        # Page 0: upload
        p0 = QWidget()
        v0 = QVBoxLayout(p0)
        v0.setContentsMargins(0, 0, 0, 0)
        self.drop = DropZone("Drag & drop an image here\nor click to browse\n(JPG, PNG, BMP, WEBP)")
        self.drop.file_dropped.connect(self._load_image_file)
        self.drop.browse_requested.connect(self._browse_image)
        row0 = QHBoxLayout()
        b_browse = QPushButton("Browse…")
        b_browse.setObjectName("primary")
        b_browse.clicked.connect(self._browse_image)
        b_clear = QPushButton("Clear")
        b_clear.clicked.connect(self._clear)
        row0.addWidget(b_browse)
        row0.addWidget(b_clear)
        row0.addStretch(1)
        v0.addWidget(self.drop, 1)
        v0.addLayout(row0)
        self.stack.addWidget(p0)

        # Page 1: camera
        p1 = QWidget()
        v1 = QVBoxLayout(p1)
        v1.setContentsMargins(0, 0, 0, 0)
        crow = QHBoxLayout()
        self.cam_combo = QComboBox()
        self.cam_combo.currentIndexChanged.connect(self._camera_selected)
        b_refresh = QPushButton("Refresh")
        b_refresh.clicked.connect(lambda: self._enter_camera(force=True))
        crow.addWidget(QLabel("Camera:"))
        crow.addWidget(self.cam_combo, 1)
        crow.addWidget(b_refresh)
        self.live = ImageView("Camera preview will appear here")
        row1 = QHBoxLayout()
        self.btn_capture = QPushButton("Capture photo")
        self.btn_capture.setObjectName("primary")
        self.btn_retake = QPushButton("Retake")
        self.btn_capture.clicked.connect(self._capture)
        self.btn_retake.clicked.connect(self._retake)
        self.btn_retake.setEnabled(False)
        row1.addWidget(self.btn_capture)
        row1.addWidget(self.btn_retake)
        row1.addStretch(1)
        v1.addLayout(crow)
        v1.addWidget(self.live, 1)
        v1.addLayout(row1)
        self.stack.addWidget(p1)

        body.addWidget(left, 5)

        self.results = ResultsPanel()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.results)
        body.addWidget(scroll, 4)

    # ------------------------------------------------------------ status / loading
    def _autoload(self):
        """Prefer ./assets next to the exe; otherwise reuse the last-used files."""
        model_p, labels_p = find_assets()
        model_p = model_p or self.cfg.value("model_path", None)
        labels_p = labels_p or self.cfg.value("labels_path", None)
        if model_p:
            self._load_model(model_p, quiet=True)
        if labels_p:
            self._load_labels(labels_p, quiet=True)
        self._refresh_status()
        if not (self.clf.model_loaded and self.clf.labels_loaded):
            self.banner.show_message("Load a .tflite model and labels.txt to get started "
                                     "(or place them in an 'assets' folder next to the app).",
                                     "info", 10)

    def _refresh_status(self):
        for chip, ok, text in ((self.chip_model, self.clf.model_loaded, "Model"),
                               (self.chip_labels, self.clf.labels_loaded, "Labels")):
            chip.setText(f"{'●' if ok else '○'} {text} {'loaded' if ok else 'missing'}")
            chip.setProperty("state", "ok" if ok else "bad")
            repolish(chip)
        self.chip_model.setToolTip(str(self.clf.model_path or ""))
        self.chip_labels.setToolTip(str(self.clf.labels_path or ""))
        info = self.clf.describe()
        if self.clf.labels_loaded:
            info += f"  |  {len(self.clf.labels)} labels"
        self.model_info.setText(info)

    def _load_model(self, path, quiet=False):
        try:
            self.clf.load_model(path)
        except Exception as e:  # corrupt file, wrong format, runtime missing...
            self.banner.show_message(f"Could not load model: {e}", "error")
            return
        self.cfg.setValue("model_path", str(path))
        self._after_load(quiet)

    def _load_labels(self, path, quiet=False):
        try:
            self.clf.load_labels(path)
        except Exception as e:
            self.banner.show_message(f"Could not load labels: {e}", "error")
            return
        self.cfg.setValue("labels_path", str(path))
        self._after_load(quiet)

    def _after_load(self, quiet):
        self._refresh_status()
        if self.clf.model_loaded and self.clf.labels_loaded:
            err = self.clf.ready_error()
            if err:
                self.banner.show_message(err, "warn", 10)
            elif not quiet:
                self.banner.show_message("Model and labels ready.", "info", 3)
            if not err and self.current_rgb is not None:
                self._run_inference()

    def _pick_model(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select TFLite model", "", "TFLite model (*.tflite)")
        if p:
            self._load_model(p)

    def _pick_labels(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select labels file", "", "Text files (*.txt)")
        if p:
            self._load_labels(p)

    def _open_settings(self):
        dlg = SettingsDialog(self, self.norm_mode, self.threshold, self.clf.describe())
        if dlg.exec():
            self.norm_mode = dlg.norm.currentData()
            self.threshold = dlg.thr.value() / 100.0
            self.cfg.setValue("norm_mode", self.norm_mode)
            self.cfg.setValue("threshold", self.threshold)
            if self.current_rgb is not None:
                self._run_inference()

    # ------------------------------------------------------------ mode switching
    def _set_mode(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx == 1:
            self._enter_camera()
        else:
            self.camera.stop()

    def _enter_camera(self, force=False):
        self.btn_retake.setEnabled(False)
        if force or not self.cam_indices:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                self.cam_indices = list_cameras()
            finally:
                QGuiApplication.restoreOverrideCursor()
            self.cam_combo.blockSignals(True)
            self.cam_combo.clear()
            for i in self.cam_indices:
                self.cam_combo.addItem(f"Camera {i}", i)
            self.cam_combo.blockSignals(False)
        if not self.cam_indices:
            self.live.clear_image()
            self.btn_capture.setEnabled(False)
            self.banner.show_message("No camera detected. Connect a webcam and press Refresh, "
                                     "or use 'Upload image'.", "warn", 10)
            return
        self.btn_capture.setEnabled(True)
        self._camera_selected()

    def _camera_selected(self, *_):
        idx = self.cam_combo.currentData()
        if idx is not None:
            self.btn_retake.setEnabled(False)
            self.btn_capture.setEnabled(self.camera.start(idx))

    # ------------------------------------------------------------ image sources
    def _browse_image(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_EXT)
        p, _ = QFileDialog.getOpenFileName(self, "Select image", "", f"Images ({exts})")
        if p:
            self._load_image_file(p)

    def _load_image_file(self, path):
        try:
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")  # honour phone rotation
                rgb = np.array(im)
        except Exception:
            self.banner.show_message("That file couldn't be opened as an image. "
                                     "Please choose a valid JPG, PNG, BMP or WEBP.", "error")
            return
        self.current_rgb = rgb
        self.drop.set_rgb(rgb)
        self._run_inference()

    def _clear(self):
        self.current_rgb = None
        self.drop.clear_image()
        self.results.show_placeholder()

    def _on_frame(self, bgr):
        self.live.set_rgb(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))

    def _capture(self):
        frame = self.camera.last_frame
        if frame is None:
            self.banner.show_message("No frame received from the camera yet - try again.", "warn")
            return
        self.camera.pause()  # freeze the preview on the captured photo
        self.current_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.live.set_rgb(self.current_rgb)
        self.btn_capture.setEnabled(False)
        self.btn_retake.setEnabled(True)
        self._run_inference()

    def _retake(self):
        self.current_rgb = None
        self.results.show_placeholder()
        self.btn_retake.setEnabled(False)
        self.btn_capture.setEnabled(True)
        self.camera.resume()

    # ------------------------------------------------------------ inference
    def _run_inference(self):
        err = self.clf.ready_error()
        if err:
            self.results.show_placeholder("Image ready - waiting for a valid model and labels.")
            self.banner.show_message(err, "warn")
            return
        try:
            probs = self.clf.predict(self.current_rgb, self.norm_mode)
        except Exception as e:
            self.banner.show_message(f"Inference failed: {e}", "error")
            return
        self.results.show_result(self.clf.labels, probs, self.threshold)

    def closeEvent(self, e):
        self.camera.stop()
        super().closeEvent(e)
