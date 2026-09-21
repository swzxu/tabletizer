@echo off
title osu! Android Tablet Connector
chcp 65001 > nul
color 0b

echo ========================================================
echo       osu! Android Tablet Connector (1-Click)
echo ========================================================
echo.

:: Check Admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Запрос прав администратора...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Check ADB
where adb >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Ошибка: adb не найден в системе (PATH).
    echo Убедитесь, что Android SDK Platform Tools установлены.
    pause
    exit /b
)

:: Wait for device
echo [*] Ожидание подключения телефона по USB (ADB)...
adb wait-for-device
echo [OK] Телефон обнаружен!

:: Forward port
echo [*] Проброс порта 3240...
adb forward tcp:3240 tcp:3240
if %errorlevel% neq 0 (
    echo [X] Не удалось выполнить adb forward.
    pause
    exit /b
)
echo [OK] Порт 3240 успешно проброшен.

:: Copy config to OTD
set "OTD_DIR=D:\Users\hrdcoreee\Desktop\OpenTabletDriver-0.6.7_win-x64"
if exist "%OTD_DIR%" (
    if not exist "%OTD_DIR%\Configurations" mkdir "%OTD_DIR%\Configurations"
    if not exist "%OTD_DIR%\userdata\Configurations" mkdir "%OTD_DIR%\userdata\Configurations"
    if exist "%~dp0AndroidTablet.json" (
        copy /y "%~dp0AndroidTablet.json" "%OTD_DIR%\Configurations\AndroidTablet.json" >nul
        copy /y "%~dp0AndroidTablet.json" "%OTD_DIR%\userdata\Configurations\AndroidTablet.json" >nul
        echo [OK] Конфигурация синхронизирована с OpenTabletDriver.
    )
)

:: Find usbip
set "USBIP_EXE="
if exist "C:\Program Files\usbip\usbip.exe" set "USBIP_EXE=C:\Program Files\usbip\usbip.exe"
if not defined USBIP_EXE if exist "C:\Program Files\usbip-win\usbip.exe" set "USBIP_EXE=C:\Program Files\usbip-win\usbip.exe"
if not defined USBIP_EXE if exist "C:\Program Files (x86)\usbip\usbip.exe" set "USBIP_EXE=C:\Program Files (x86)\usbip\usbip.exe"
if not defined USBIP_EXE if exist "C:\Program Files (x86)\usbip-win\usbip.exe" set "USBIP_EXE=C:\Program Files (x86)\usbip-win\usbip.exe"
if not defined USBIP_EXE if exist "%~dp0bin\usbip\usbip.exe" set "USBIP_EXE=%~dp0bin\usbip\usbip.exe"
if not defined USBIP_EXE if exist "%~dp0desktop_client\bin\usbip\usbip.exe" set "USBIP_EXE=%~dp0desktop_client\bin\usbip\usbip.exe"
if not defined USBIP_EXE where usbip >nul 2>&1 && set "USBIP_EXE=usbip"

if not defined USBIP_EXE (
    echo [X] usbip.exe не найден в Program Files или PATH.
    pause
    exit /b
)

:: Attach
echo [*] Подключение устройства USB/IP...
"%USBIP_EXE%" attach -r 127.0.0.1 -b 1-1
echo.
echo ========================================================
echo  [УСПЕХ] Телефон подключен как графический планшет!
echo  OpenTabletDriver активен.
echo ========================================================
echo.
echo [Совет] Если провод отошел или приложение перезапущено:
echo Просто нажми [ENTER] в этом окне для быстрого переподключения.
echo.

:loop
pause >nul
echo [*] Переподключение...
"%USBIP_EXE%" detach -p 0 >nul 2>&1
adb forward tcp:3240 tcp:3240 >nul 2>&1
"%USBIP_EXE%" attach -r 127.0.0.1 -b 1-1
echo [OK] Устройство переподключено!
goto loop
