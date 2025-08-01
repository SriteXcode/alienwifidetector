@echo off
REM ===== Build script for WiFi Clone Detector =====
echo Building WiFi Clone Detector .exe ...
pyinstaller --onefile --noconsole ^
--icon=alienwifidetector\icon.ico ^
--name="WiFi Clone Detector" ^
--version-file=version_info.txt ^
main2.py
echo.
echo Build complete! Check the "dist" folder for WiFi Clone Detector.exe
pause
