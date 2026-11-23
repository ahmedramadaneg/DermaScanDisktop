@echo off
REM ===== DermaScan Desktop - Windows build =====
REM Requires 64-bit Python 3.11 (https://www.python.org/downloads/windows/)

py -3.11 -m venv .venv || goto :err
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller || goto :err

REM Optional: single-file exe  ->  uncomment the next line
REM set ONEFILE=1

pyinstaller --noconfirm --clean DermaScan.spec || goto :err

REM Ship editable assets next to the exe (override the bundled copy)
if exist dist\DermaScanDesktop\DermaScanDesktop.exe (
    xcopy /E /I /Y assets dist\DermaScanDesktop\assets >nul
    echo Done: dist\DermaScanDesktop\DermaScanDesktop.exe
) else (
    xcopy /E /I /Y assets dist\assets >nul
    echo Done: dist\DermaScanDesktop.exe  ^(assets folder in dist\assets^)
)
exit /b 0
:err
echo BUILD FAILED
exit /b 1
