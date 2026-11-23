"""DermaScan Desktop - entry point.

Run the GUI:      python main.py
Headless check:   python main.py --selftest path/to/image.jpg
"""
import sys


def selftest(image_path: str) -> int:
    """Load the bundled model/labels and classify one image without opening a window."""
    from PIL import Image, ImageOps
    import numpy as np
    from core.model import Classifier
    from core.paths import find_assets

    model_p, labels_p = find_assets()
    if not model_p or not labels_p:
        print("assets/ model or labels.txt not found")
        return 1
    clf = Classifier()
    clf.load_model(model_p)
    clf.load_labels(labels_p)
    print(clf.describe())
    err = clf.ready_error()
    if err:
        print("ERROR:", err)
        return 1
    img = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
    probs = clf.predict(np.array(img))
    for i in np.argsort(probs)[::-1]:
        print(f"{clf.labels[i]:>6}  {probs[i] * 100:6.2f}%")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest(sys.argv[sys.argv.index("--selftest") + 1])

    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow
    from ui.styles import QSS

    app = QApplication(sys.argv)
    app.setApplicationName("DermaScan Desktop")
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
