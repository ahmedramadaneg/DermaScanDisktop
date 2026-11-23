# DermaScan Desktop

Offline skin-lesion screening prototype (PySide6 + OpenCV + TFLite). **Educational/research
use only - not a medical diagnosis.**

## Run from source
```
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
Headless check (no window): `python main.py --selftest some_image.jpg`

## Build the .exe
Double-click `build.bat` (or run it in a terminal). Output:
- `dist\DermaScanDesktop\DermaScanDesktop.exe` (folder build, recommended: starts in seconds)
- For one single file: remove `REM` from `set ONEFILE=1` in build.bat -> `dist\DermaScanDesktop.exe`
  (starts slowly because TensorFlow unpacks to a temp folder on every launch).

## Model & labels
Order of lookup at startup: `assets\` next to the .exe -> copy bundled inside the build ->
last files you picked. You can always use **Load model… / Load labels…**.
Label order in `labels.txt` must match the model's output order.

## Settings
- Input normalisation: default `(pixel/127.5)-1`. If predictions look biased toward one class,
  try `pixel/255` - the correct choice is whatever the model was trained with.
- Inconclusive threshold: default 50 %.
