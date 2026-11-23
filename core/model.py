"""TFLite / LiteRT wrapper: model + labels loading, preprocessing, inference."""
from pathlib import Path

import cv2
import numpy as np

# Normalisation presets. The default matches the requested MobileNetV2 preprocessing.
NORM_MODES = {
    "mobilenet_v2": "MobileNetV2: (pixel / 127.5) - 1  ->  [-1, 1]",
    "unit": "Unit range: pixel / 255  ->  [0, 1]",
    "raw": "Raw: 0-255 float, no scaling",
}


def _import_interpreter():
    """Use whichever TFLite-capable runtime is installed (no internet needed)."""
    try:
        from ai_edge_litert.interpreter import Interpreter  # LiteRT
        return Interpreter, "LiteRT"
    except ImportError:
        pass
    try:
        from tflite_runtime.interpreter import Interpreter
        return Interpreter, "tflite-runtime"
    except ImportError:
        pass
    try:
        import tensorflow as tf
        return tf.lite.Interpreter, "TensorFlow Lite"
    except ImportError as e:
        raise RuntimeError(
            "No TFLite runtime found. Install tensorflow, ai-edge-litert or tflite-runtime."
        ) from e


def normalize(img_uint8: np.ndarray, mode: str) -> np.ndarray:
    x = img_uint8.astype(np.float32)
    if mode == "mobilenet_v2":
        return x / 127.5 - 1.0
    if mode == "unit":
        return x / 255.0
    return x


class Classifier:
    def __init__(self):
        self.interp = None
        self.runtime = ""
        self.model_path = None
        self.labels_path = None
        self.labels = []
        self.inp = None
        self.out = None
        self.input_hw = (224, 224)

    # ---------- loading ----------
    def load_model(self, path) -> None:
        Interpreter, runtime = _import_interpreter()
        interp = Interpreter(model_path=str(path), num_threads=4)
        interp.allocate_tensors()
        inp = interp.get_input_details()[0]
        out = interp.get_output_details()[0]
        shape = inp["shape"]
        if len(shape) != 4 or shape[-1] != 3:
            raise ValueError(f"Unsupported input shape {list(shape)}; expected [1, H, W, 3].")
        # Commit only after everything validated, so a bad file never breaks a good model.
        self.interp, self.runtime, self.inp, self.out = interp, runtime, inp, out
        self.input_hw = (int(shape[1]), int(shape[2]))
        self.model_path = Path(path)

    def load_labels(self, path) -> None:
        lines = [l.strip() for l in Path(path).read_text(encoding="utf-8-sig").splitlines()]
        labels = [l for l in lines if l]
        if not labels:
            raise ValueError("The labels file is empty.")
        self.labels, self.labels_path = labels, Path(path)

    # ---------- status ----------
    @property
    def model_loaded(self) -> bool:
        return self.interp is not None

    @property
    def labels_loaded(self) -> bool:
        return bool(self.labels)

    @property
    def num_outputs(self) -> int:
        return int(np.prod(self.out["shape"][1:])) if self.out is not None else 0

    def ready_error(self):
        """Friendly reason why inference can't run, or None if everything is fine."""
        if not self.model_loaded:
            return "Load a .tflite model first."
        if not self.labels_loaded:
            return "Load a labels.txt file first."
        if len(self.labels) != self.num_outputs:
            return (f"labels.txt has {len(self.labels)} entries but the model outputs "
                    f"{self.num_outputs} classes. Please load matching files.")
        return None

    def describe(self) -> str:
        if not self.model_loaded:
            return "No model loaded"
        i, o = self.inp, self.out
        return (f"Input {list(map(int, i['shape']))} {np.dtype(i['dtype']).name}  ->  "
                f"Output {list(map(int, o['shape']))} {np.dtype(o['dtype']).name}  |  {self.runtime}")

    # ---------- inference ----------
    def predict(self, rgb_uint8: np.ndarray, norm_mode: str = "mobilenet_v2") -> np.ndarray:
        """rgb_uint8: HxWx3 RGB image. Returns a probability vector (sums to 1)."""
        h, w = self.input_hw
        img = cv2.resize(rgb_uint8, (w, h), interpolation=cv2.INTER_LINEAR)  # 224x224 RGB
        x = normalize(img, norm_mode)[None, ...]

        dt = np.dtype(self.inp["dtype"])
        if dt.kind == "f":
            tensor = x.astype(dt)
        else:  # quantised integer input (not the case for fp16 models, kept for safety)
            scale, zp = self.inp["quantization"]
            info = np.iinfo(dt)
            tensor = np.clip(np.round(x / (scale or 1.0) + zp), info.min, info.max).astype(dt)

        self.interp.set_tensor(self.inp["index"], tensor)
        self.interp.invoke()
        out = self.interp.get_tensor(self.out["index"]).reshape(-1)

        if out.dtype.kind != "f":
            scale, zp = self.out["quantization"]
            out = (out.astype(np.float32) - zp) * (scale or 1.0)
        out = out.astype(np.float32)

        # Model already ends with softmax -> keep as is; otherwise apply softmax.
        if out.min() < 0 or abs(float(out.sum()) - 1.0) > 1e-2:
            e = np.exp(out - out.max())
            out = e / e.sum()
        return out
