@echo off
pip install pyinstaller
timeout /t 2
pip install customtkinter
timeout /t 2
pyinstaller --onefile --windowed --icon=icon.ico --add-data "icon.ico;." main.py
pause