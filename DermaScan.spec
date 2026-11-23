# PyInstaller spec for DermaScan Desktop.
#   Folder build (default, fast start):   pyinstaller --noconfirm --clean DermaScan.spec
#   Single-file build (slow first start): set ONEFILE=1 first (see build.bat)
import importlib.util
import os
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []

# Bundle the default model + labels INSIDE the build. Files in an 'assets' folder next to
# the .exe still take priority at runtime, so users can swap models without rebuilding.
if os.path.isdir("assets"):
    datas.append(("assets", "assets"))

# Pull in the TFLite runtime that is installed (same priority order as core/model.py).
for pkg in ("ai_edge_litert", "tflite_runtime", "tensorflow"):
    if importlib.util.find_spec(pkg):
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
        break

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "pytest", "IPython"],
)
pyz = PYZ(a.pure)

if os.environ.get("ONEFILE") == "1":
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
              name="DermaScanDesktop", console=False, upx=False)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
              name="DermaScanDesktop", console=False, upx=False)
    coll = COLLECT(exe, a.binaries, a.datas, name="DermaScanDesktop", upx=False)
