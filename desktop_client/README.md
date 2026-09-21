# osu! Tablet Companion for Android (PC Client)

A lightweight, modern Windows GUI companion designed for osu! players to use their Android phone or tablet as a graphics drawing tablet with **OpenTabletDriver** and **USB/IP**.

---

## ✨ Features
* **100% English UI** with modern dark aesthetics.
* **One-Click Connect / Disconnect**: Handles `adb forward` and `usbip attach` automatically without touching the terminal.
* **Auto-Dependency Checker**:
  * Detects if **Android Platform Tools (ADB)** is installed. If missing, downloads and sets it up directly from Google with a single click.
  * Detects if **USB/IP** is available. Offers direct download or links to official releases.
* **Auto-Profile Sync**:
  * Automatically detects OpenTabletDriver installation and copies `AndroidTablet.json` to both `Configurations/` and `userdata/Configurations/`.
* **Phone Auto-Detection**:
  * Displays connected phone model name and ADB serial ID in real-time.
* **Wired & Wireless Support**:
  * Supports ultra-low-latency wired USB (recommended for osu!) and wireless local IP mode.

---

## 🚀 How to Run
1. Ensure **Python 3** is installed on your computer.
2. Double-click `run.bat` (or run `python main.py` in terminal).
3. If prompted, click **"Restart as Admin"** (Administrator rights are needed for USB/IP attach to bind the driver).
4. Click **"Download ADB"** or **"Get USB/IP"** if any requirements are marked as missing.
5. Click **"Install Profile"** to configure OpenTabletDriver automatically.
6. Connect your phone via USB, open the **Tablet Server** app on your phone, and click **⚡ CONNECT TABLET**!
