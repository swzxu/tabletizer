@echo off
pip install pyinstaller
timeout /t 2
pip install customtkinter
timeout /t 2
pip install pystray pillow
timeout /t 2
pyinstaller --onefile --windowed --icon=icon.ico --add-data "icon.ico;." --add-data "..\driver;driver" --uac-admin --name "tabletizer" main.py