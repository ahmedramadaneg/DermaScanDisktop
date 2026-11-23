"""Application stylesheet (light, clean, teal accent)."""
QSS = """
* { font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; color: #1f2933; }
QMainWindow, QDialog { background: #f3f6f8; }
QFrame#card { background: #ffffff; border: 1px solid #e1e8ed; border-radius: 14px; }
QLabel#title { font-size: 22px; font-weight: 700; }
QLabel#subtitle { color: #6b7c88; font-size: 12px; }
QLabel#cardTitle { font-size: 15px; font-weight: 600; }
QLabel#headline { font-size: 24px; font-weight: 700; }
QLabel#muted { color: #6b7c88; }
QLabel#disclaimer { background: #fff7e6; border: 1px solid #ffd591; border-radius: 10px;
                    padding: 10px; color: #7a4b00; font-size: 12px; }

QLabel#chip { border-radius: 11px; padding: 3px 10px; font-weight: 600; font-size: 12px; }
QLabel#chip[state="ok"]  { background: #e3f8ec; color: #137a43; }
QLabel#chip[state="bad"] { background: #fdecea; color: #b3261e; }

QLabel#banner { border-radius: 10px; padding: 10px 14px; font-weight: 500; }
QLabel#banner[level="info"]  { background: #e6f4ff; color: #0b5394; border: 1px solid #b6dcfb; }
QLabel#banner[level="warn"]  { background: #fff7e6; color: #7a4b00; border: 1px solid #ffd591; }
QLabel#banner[level="error"] { background: #fdecea; color: #8c1d18; border: 1px solid #f5b5b0; }

QLabel#badge { border-radius: 8px; padding: 6px 10px; font-weight: 600; }
QLabel#badge[risk="high"] { background: #fdecea; color: #b3261e; }
QLabel#badge[risk="moderate"] { background: #fff1e0; color: #a85a00; }
QLabel#badge[risk="low"] { background: #e3f8ec; color: #137a43; }
QLabel#badge[risk="unknown"] { background: #eceff1; color: #455a64; }

QLabel#imageView { background: #f8fafb; border: 2px dashed #c9d5dd; border-radius: 12px; color: #6b7c88; }
QLabel#imageView[filled="true"] { border: 1px solid #e1e8ed; background: #11181d; }
QLabel#imageView[hover="true"] { border-color: #0f9d8a; background: #eefaf8; }

QPushButton { background: #ffffff; border: 1px solid #cfd9e0; border-radius: 9px; padding: 8px 14px; font-weight: 600; }
QPushButton:hover { background: #f0f5f8; }
QPushButton:disabled { color: #a3b1bb; background: #f5f7f9; }
QPushButton#primary { background: #0f9d8a; border: 1px solid #0f9d8a; color: white; }
QPushButton#primary:hover { background: #0c8473; }
QPushButton#primary:disabled { background: #a9d9d2; border-color: #a9d9d2; color: white; }
QPushButton#mode { border-radius: 9px; }
QPushButton#mode:checked { background: #0f9d8a; color: white; border-color: #0f9d8a; }

QComboBox, QDoubleSpinBox { border: 1px solid #cfd9e0; border-radius: 8px; padding: 6px 8px; background: white; }
QProgressBar { background: #e9eef2; border: none; border-radius: 5px; max-height: 10px; min-height: 10px; }
QProgressBar::chunk { border-radius: 5px; background: #9fb3c0; }
QProgressBar[top="true"]::chunk { background: #0f9d8a; }
QScrollArea { border: none; background: transparent; }
"""
