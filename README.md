# tabletizer!

A tool that allows you to use your Android device as a graphics tablet on Windows, it was created primarily for osu!.

The project consists of two components:
1. An Android application that acts as a USB/IP server, capturing touch and pen inputs.
2. A Windows desktop client that automates dependency management (ADB, USB/IP), profile generation, and connection handling.

## Requirements

- Windows 10/11
- OpenTabletDriver installed on the PC
- Developer Options and USB Debugging enabled on the Android device (required for wired connections or automated profile generation)
- More requirements that you can install from companion app


## Setup

1. Install the tabletizer APK on your Android device.
2. Launch the desktop client on your desktop.
3. Click "Auto-Generate Profile" in the desktop client while the device is connected via USB. This will automatically query your screen resolution and DPI to generate an accurate OpenTabletDriver configuration.
   - Alternatively, use "Manual Config" to input your device's screen width, height, and DPI manually without requiring an ADB connection.

## Usage

You can connect the device to your PC either via a USB cable or over the local Wi-Fi network.

### Wired (USB)
1. Enable ADB in developer settings on you phone and connect your device to the PC via USB.
2. Select the "Wired (USB)" mode in the desktop client and click "Connect".
3. Open the tabletizer app on your Android device.

### Wireless (Wi-Fi)
1. Ensure both devices are connected to the same local network.
2. Open the tabletizer app on your Android device.
3. Select the "Wireless (Wi-Fi)" mode in the desktop client, enter the IP address of your device, and click "Connect".

## Building from Source

### Android App
To compile the APK using Gradle:
```bash
./gradlew assembleDebug
```

### Desktop Client
To build a standalone Windows executable, ensure Python 3 is installed and run:
```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --icon NONE --windowed desktop_client/main.py
```
