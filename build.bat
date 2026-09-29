@echo off
echo ========================================================
echo   Building Drone Flight Simulator Executable (PyInstaller)
echo ========================================================

pip install -r requirements.txt

pyinstaller --noconfirm --onedir --windowed ^
    --name "DroneFlightSimulator" ^
    --collect-all ursina ^
    --collect-all panda3d ^
    main.py

echo.
echo ========================================================
echo   Build complete! Output located at: dist\DroneFlightSimulator\
echo ========================================================
pause